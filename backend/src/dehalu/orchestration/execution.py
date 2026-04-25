from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Protocol

from dehalu.adapters.llm import LLMProvider
from dehalu.agents import CrewAIRunner, CrewExecutionContext, CrewTaskDefinition
from dehalu.agents.roles import CODER_AGENT, REPAIR_AGENT, VERIFIER_AGENT
from dehalu.schemas import (
    CoderOutput,
    NormalizedRequest,
    RepairAttempt,
    RepairOutcome,
    RepairResult,
    RepairTrigger,
)
from dehalu.state.repository import EvaluationBundle
from dehalu.verification.claims import ClaimExtractor
from dehalu.verification.policy import PolicyEngine
from dehalu.verification.sandbox import SandboxVerifier
from dehalu.verification.static_analysis import StaticAnalyzer


@dataclass(slots=True)
class ExecutionResult:
    initial_attempt: EvaluationBundle
    final_attempt: EvaluationBundle
    repair_result: RepairResult


class RunExecutionEngine(Protocol):
    def execute(
        self,
        normalized: NormalizedRequest,
        provider: LLMProvider,
    ) -> ExecutionResult:
        raise NotImplementedError


class _BaseExecutionEngine:
    def __init__(
        self,
        claim_extractor: ClaimExtractor,
        static_analyzer: StaticAnalyzer,
        sandbox_verifier: SandboxVerifier,
        policy_engine: PolicyEngine,
    ) -> None:
        self.claim_extractor = claim_extractor
        self.static_analyzer = static_analyzer
        self.sandbox_verifier = sandbox_verifier
        self.policy_engine = policy_engine

    def _evaluate_attempt(
        self,
        normalized: NormalizedRequest,
        provider: LLMProvider,
        coder_output: CoderOutput,
        *,
        attempt_number: int,
        attempt_stage: str,
        allow_repair: bool,
    ) -> EvaluationBundle:
        extracted_claims = self.claim_extractor.extract(coder_output)
        static_findings = self.static_analyzer.analyze(
            coder_output.code,
            normalized.language,
        )
        sandbox_result = self.sandbox_verifier.verify(
            coder_output.code,
            normalized.language,
        )
        judge_result = provider.judge(
            normalized,
            coder_output,
            extracted_claims,
            static_findings,
            sandbox_result,
        )
        cove_result = provider.cove(
            normalized,
            coder_output,
            extracted_claims,
            static_findings,
            sandbox_result,
            judge_result,
        )
        policy_decision = self.policy_engine.decide(
            static_findings,
            normalized.risk_level,
            sandbox_result,
            judge_result,
            cove_result,
            allow_repair=allow_repair,
        )
        return EvaluationBundle(
            attempt_number=attempt_number,
            attempt_stage=attempt_stage,
            coder_output=coder_output,
            extracted_claims=extracted_claims,
            static_findings=static_findings,
            sandbox_result=sandbox_result,
            judge_result=judge_result,
            cove_result=cove_result,
            policy_decision=policy_decision,
        )

    def _build_repair_result(
        self,
        initial_attempt: EvaluationBundle,
        final_attempt: EvaluationBundle,
        repair_attempt: RepairAttempt | None,
    ) -> RepairResult:
        if repair_attempt is None:
            return RepairResult(
                outcome=RepairOutcome.skipped,
                attempts=[],
                final_attempt_number=1,
                metrics={
                    "attempted": False,
                    "initial_policy_state": initial_attempt.policy_decision.state.value,
                    "final_policy_state": final_attempt.policy_decision.state.value,
                },
            )
        return RepairResult(
            outcome=(
                RepairOutcome.succeeded
                if final_attempt.policy_decision.state.value == "accept"
                else RepairOutcome.failed
            ),
            attempts=[repair_attempt],
            final_attempt_number=2,
            metrics={
                "attempted": True,
                "initial_policy_state": initial_attempt.policy_decision.state.value,
                "final_policy_state": final_attempt.policy_decision.state.value,
                "trigger": repair_attempt.trigger.value,
            },
        )

    def _repair_attempt(
        self,
        normalized: NormalizedRequest,
        provider: LLMProvider,
        initial_attempt: EvaluationBundle,
    ) -> tuple[EvaluationBundle, RepairAttempt]:
        repair_trigger = RepairTrigger(
            initial_attempt.policy_decision.metrics["repair_trigger"]
        )
        repair_started_at = perf_counter()
        repaired_output = provider.repair(
            normalized,
            initial_attempt.coder_output,
            initial_attempt.policy_decision,
            initial_attempt.judge_result,
            initial_attempt.cove_result,
        )
        repair_attempt = RepairAttempt(
            attempt_number=2,
            trigger=repair_trigger,
            provider=repaired_output.provider,
            model=repaired_output.model,
            duration_ms=round((perf_counter() - repair_started_at) * 1000, 3),
            input_code=initial_attempt.coder_output.code,
            output_code=repaired_output.code,
            summary=_summarize_repair(initial_attempt.coder_output, repaired_output),
            metadata={"execution_notes": repaired_output.execution_notes},
        )
        final_attempt = self._evaluate_attempt(
            normalized,
            provider,
            repaired_output,
            attempt_number=2,
            attempt_stage="repair",
            allow_repair=False,
        )
        return final_attempt, repair_attempt


class DirectExecutionEngine(_BaseExecutionEngine):
    def execute(
        self,
        normalized: NormalizedRequest,
        provider: LLMProvider,
    ) -> ExecutionResult:
        initial_output = provider.generate(normalized)
        initial_attempt = self._evaluate_attempt(
            normalized,
            provider,
            initial_output,
            attempt_number=1,
            attempt_stage="original",
            allow_repair=True,
        )
        final_attempt = initial_attempt
        repair_attempt: RepairAttempt | None = None
        if initial_attempt.policy_decision.state.value == "repair_and_retry":
            final_attempt, repair_attempt = self._repair_attempt(
                normalized,
                provider,
                initial_attempt,
            )
        return ExecutionResult(
            initial_attempt=initial_attempt,
            final_attempt=final_attempt,
            repair_result=self._build_repair_result(
                initial_attempt,
                final_attempt,
                repair_attempt,
            ),
        )


class CrewAIExecutionEngine(_BaseExecutionEngine):
    def __init__(
        self,
        claim_extractor: ClaimExtractor,
        static_analyzer: StaticAnalyzer,
        sandbox_verifier: SandboxVerifier,
        policy_engine: PolicyEngine,
        runner: CrewAIRunner | None = None,
    ) -> None:
        super().__init__(claim_extractor, static_analyzer, sandbox_verifier, policy_engine)
        self.runner = runner or CrewAIRunner(verbose=False)

    def execute(
        self,
        normalized: NormalizedRequest,
        provider: LLMProvider,
    ) -> ExecutionResult:
        context = CrewExecutionContext(
            normalized_request=normalized,
            provider=provider,
        )

        def generate(context: CrewExecutionContext) -> None:
            context.generated_output = provider.generate(normalized)

        def verify(context: CrewExecutionContext) -> None:
            if context.generated_output is None:
                raise ValueError("CrewAI generation task did not produce output.")
            context.initial_attempt = self._evaluate_attempt(
                normalized,
                provider,
                context.generated_output,
                attempt_number=1,
                attempt_stage="original",
                allow_repair=True,
            )
            context.final_attempt = context.initial_attempt
            context.repair_result = self._build_repair_result(
                context.initial_attempt,
                context.final_attempt,
                None,
            )

        def repair(context: CrewExecutionContext) -> None:
            if context.initial_attempt is None:
                raise ValueError("CrewAI verify task did not produce an initial attempt.")
            if context.initial_attempt.policy_decision.state.value != "repair_and_retry":
                return
            context.final_attempt, repair_attempt = self._repair_attempt(
                normalized,
                provider,
                context.initial_attempt,
            )
            context.repair_result = self._build_repair_result(
                context.initial_attempt,
                context.final_attempt,
                repair_attempt,
            )

        task_definitions = [
            CrewTaskDefinition(
                name="generate_output",
                description="Generate the initial coder output for verification.",
                expected_output="A coder output object ready for verification.",
                agent_role=CODER_AGENT["role"],
                run=generate,
            ),
            CrewTaskDefinition(
                name="verify_output",
                description="Run backend-owned verification on the generated output.",
                expected_output="An initial evaluation bundle with policy decision.",
                agent_role=VERIFIER_AGENT["role"],
                run=verify,
            ),
            CrewTaskDefinition(
                name="repair_output",
                description="Perform one repair-and-retry pass when policy requests mitigation.",
                expected_output="A final evaluation bundle and repair result.",
                agent_role=REPAIR_AGENT["role"],
                run=repair,
            ),
        ]
        context = self.runner.run(context, task_definitions)
        if context.initial_attempt is None or context.final_attempt is None or context.repair_result is None:
            raise ValueError("CrewAI execution did not produce a complete run result.")
        return ExecutionResult(
            initial_attempt=context.initial_attempt,
            final_attempt=context.final_attempt,
            repair_result=context.repair_result,
        )


def build_execution_engine(
    settings_mode: str,
    claim_extractor: ClaimExtractor,
    static_analyzer: StaticAnalyzer,
    sandbox_verifier: SandboxVerifier,
    policy_engine: PolicyEngine,
) -> RunExecutionEngine:
    if settings_mode == "crewai":
        return CrewAIExecutionEngine(
            claim_extractor,
            static_analyzer,
            sandbox_verifier,
            policy_engine,
        )
    return DirectExecutionEngine(
        claim_extractor,
        static_analyzer,
        sandbox_verifier,
        policy_engine,
    )


def _summarize_repair(original_output: CoderOutput, repaired_output: CoderOutput) -> str:
    if not repaired_output.code.strip():
        return "Repair attempt did not return code."
    if repaired_output.code.strip() == original_output.code.strip():
        return "Repair attempt returned code unchanged."
    return "Repair attempt returned revised code for re-verification."
