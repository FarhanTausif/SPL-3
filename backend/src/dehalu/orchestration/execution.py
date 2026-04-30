from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Protocol

from dehalu.adapters.llm import LLMProvider
from dehalu.agents import CrewAIRunner, CrewExecutionContext, CrewTaskSpec, OrchestrationTraceEntry
from dehalu.agents.roles import (
    CLAIM_EXTRACTOR_AGENT,
    COVE_AGENT,
    GENERATOR_AGENT,
    JUDGE_AGENT,
    POLICY_COORDINATOR_AGENT,
    REPAIR_AGENT,
    STATIC_VERIFIER_AGENT,
)
from dehalu.schemas import (
    CoderOutput,
    ExtractedClaim,
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

ORIGINAL_GENERATED_OUTPUT = "original.generated_output"
ORIGINAL_EXTRACTED_CLAIMS = "original.extracted_claims"
ORIGINAL_STATIC_FINDINGS = "original.static_findings"
ORIGINAL_SANDBOX_RESULT = "original.sandbox_result"
ORIGINAL_JUDGE_RESULT = "original.judge_result"
ORIGINAL_COVE_RESULT = "original.cove_result"
ORIGINAL_POLICY_DECISION = "original.policy_decision"
INITIAL_ATTEMPT = "initial_attempt"

REPAIR_GENERATED_OUTPUT = "repair.generated_output"
REPAIR_EXTRACTED_CLAIMS = "repair.extracted_claims"
REPAIR_STATIC_FINDINGS = "repair.static_findings"
REPAIR_SANDBOX_RESULT = "repair.sandbox_result"
REPAIR_JUDGE_RESULT = "repair.judge_result"
REPAIR_COVE_RESULT = "repair.cove_result"
REPAIR_POLICY_DECISION = "repair.policy_decision"
FINAL_ATTEMPT = "final_attempt"
REPAIR_ATTEMPT = "repair_attempt"


@dataclass(slots=True)
class ExecutionResult:
    initial_attempt: EvaluationBundle
    final_attempt: EvaluationBundle
    repair_result: RepairResult
    orchestration_trace: list[OrchestrationTraceEntry]


class RunExecutionEngine(Protocol):
    def execute(
        self,
        normalized: NormalizedRequest,
        provider: LLMProvider,
    ) -> ExecutionResult:
        raise NotImplementedError


class _ExecutionStages:
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

    def generate_initial_output(self, context: CrewExecutionContext) -> None:
        generated_output = context.provider.generate(context.normalized_request)
        context.reset_attempt_state(
            attempt_number=1,
            attempt_stage="original",
            generated_output=generated_output,
        )
        context.set_artifact(ORIGINAL_GENERATED_OUTPUT, generated_output)

    def extract_claims(self, context: CrewExecutionContext, *, output_key: str) -> None:
        generated_output = self._require_generated_output(context)
        extracted_claims = self.claim_extractor.extract(generated_output)
        context.extracted_claims = extracted_claims
        context.set_artifact(output_key, extracted_claims)

    def run_static_analysis(self, context: CrewExecutionContext, *, output_key: str) -> None:
        generated_output = self._require_generated_output(context)
        static_findings = self.static_analyzer.analyze(
            generated_output.code,
            context.normalized_request.language,
        )
        context.static_findings = static_findings
        context.set_artifact(output_key, static_findings)

    def run_sandbox_verification(self, context: CrewExecutionContext, *, output_key: str) -> None:
        generated_output = self._require_generated_output(context)
        sandbox_result = self.sandbox_verifier.verify(
            generated_output.code,
            context.normalized_request.language,
        )
        context.sandbox_result = sandbox_result
        context.set_artifact(output_key, sandbox_result)

    def run_judge(self, context: CrewExecutionContext, *, output_key: str) -> None:
        generated_output = self._require_generated_output(context)
        context.judge_result = context.provider.judge(
            context.normalized_request,
            generated_output,
            context.extracted_claims,
            context.static_findings,
            self._require_sandbox_result(context),
        )
        context.set_artifact(output_key, context.judge_result)

    def run_cove(self, context: CrewExecutionContext, *, output_key: str) -> None:
        generated_output = self._require_generated_output(context)
        context.cove_result = context.provider.cove(
            context.normalized_request,
            generated_output,
            context.extracted_claims,
            context.static_findings,
            self._require_sandbox_result(context),
            self._require_judge_result(context),
        )
        context.set_artifact(output_key, context.cove_result)

    def decide_policy(
        self,
        context: CrewExecutionContext,
        *,
        output_key: str,
        allow_repair: bool,
        target_attempt_key: str,
    ) -> None:
        context.policy_decision = self.policy_engine.decide(
            context.static_findings,
            context.normalized_request.risk_level,
            self._require_sandbox_result(context),
            self._require_judge_result(context),
            self._require_cove_result(context),
            allow_repair=allow_repair,
        )
        context.set_artifact(output_key, context.policy_decision)
        bundle = self._build_evaluation_bundle(context)
        if target_attempt_key == INITIAL_ATTEMPT:
            context.initial_attempt = bundle
        context.final_attempt = bundle
        context.set_artifact(target_attempt_key, bundle)

    def generate_repair_output(self, context: CrewExecutionContext) -> None:
        if context.initial_attempt is None:
            raise ValueError("Repair cannot run before the initial attempt exists.")
        repair_trigger = RepairTrigger(context.initial_attempt.policy_decision.metrics["repair_trigger"])
        repair_started_at = perf_counter()
        repaired_output = context.provider.repair(
            context.normalized_request,
            context.initial_attempt.coder_output,
            context.initial_attempt.policy_decision,
            context.initial_attempt.judge_result,
            context.initial_attempt.cove_result,
        )
        repair_attempt = RepairAttempt(
            attempt_number=2,
            trigger=repair_trigger,
            provider=repaired_output.provider,
            model=repaired_output.model,
            duration_ms=round((perf_counter() - repair_started_at) * 1000, 3),
            input_code=context.initial_attempt.coder_output.code,
            output_code=repaired_output.code,
            summary=_summarize_repair(context.initial_attempt.coder_output, repaired_output),
            metadata={
                "execution_notes": repaired_output.execution_notes,
                "provider_invocation": repaired_output.metadata.get("provider_invocation"),
            },
        )
        context.set_artifact(REPAIR_ATTEMPT, repair_attempt)
        context.reset_attempt_state(
            attempt_number=2,
            attempt_stage="repair",
            generated_output=repaired_output,
        )
        context.set_artifact(REPAIR_GENERATED_OUTPUT, repaired_output)

    def build_repair_result(self, context: CrewExecutionContext) -> RepairResult:
        if context.initial_attempt is None or context.final_attempt is None:
            raise ValueError("Repair result requires both initial and final attempts.")
        repair_attempt = context.get_artifact(REPAIR_ATTEMPT)
        if repair_attempt is None:
            return RepairResult(
                outcome=RepairOutcome.skipped,
                attempts=[],
                final_attempt_number=1,
                metrics={
                    "attempted": False,
                    "initial_policy_state": context.initial_attempt.policy_decision.state.value,
                    "final_policy_state": context.final_attempt.policy_decision.state.value,
                },
            )
        return RepairResult(
            outcome=(
                RepairOutcome.succeeded
                if context.final_attempt.policy_decision.state.value == "accept"
                else RepairOutcome.failed
            ),
            attempts=[repair_attempt],
            final_attempt_number=2,
            metrics={
                "attempted": True,
                "initial_policy_state": context.initial_attempt.policy_decision.state.value,
                "final_policy_state": context.final_attempt.policy_decision.state.value,
                "trigger": repair_attempt.trigger.value,
            },
        )

    def _build_evaluation_bundle(self, context: CrewExecutionContext) -> EvaluationBundle:
        generated_output = self._require_generated_output(context)
        sandbox_result = self._require_sandbox_result(context)
        judge_result = self._require_judge_result(context)
        cove_result = self._require_cove_result(context)
        policy_decision = self._require_policy_decision(context)
        return EvaluationBundle(
            attempt_number=context.attempt_number,
            attempt_stage=context.attempt_stage,
            coder_output=generated_output,
            extracted_claims=list(context.extracted_claims),
            static_findings=list(context.static_findings),
            sandbox_result=sandbox_result,
            judge_result=judge_result,
            cove_result=cove_result,
            policy_decision=policy_decision,
        )

    def _require_generated_output(self, context: CrewExecutionContext) -> CoderOutput:
        if context.generated_output is None:
            raise ValueError("Generation stage did not produce output.")
        return context.generated_output

    def _require_sandbox_result(self, context: CrewExecutionContext):
        if context.sandbox_result is None:
            raise ValueError("Sandbox verification did not produce a result.")
        return context.sandbox_result

    def _require_judge_result(self, context: CrewExecutionContext):
        if context.judge_result is None:
            raise ValueError("Judge stage did not produce a result.")
        return context.judge_result

    def _require_cove_result(self, context: CrewExecutionContext):
        if context.cove_result is None:
            raise ValueError("CoVe stage did not produce a result.")
        return context.cove_result

    def _require_policy_decision(self, context: CrewExecutionContext):
        if context.policy_decision is None:
            raise ValueError("Policy stage did not produce a decision.")
        return context.policy_decision


class _BaseExecutionEngine:
    def __init__(
        self,
        claim_extractor: ClaimExtractor,
        static_analyzer: StaticAnalyzer,
        sandbox_verifier: SandboxVerifier,
        policy_engine: PolicyEngine,
    ) -> None:
        self.stages = _ExecutionStages(
            claim_extractor,
            static_analyzer,
            sandbox_verifier,
            policy_engine,
        )


class DirectExecutionEngine(_BaseExecutionEngine):
    def execute(
        self,
        normalized: NormalizedRequest,
        provider: LLMProvider,
    ) -> ExecutionResult:
        context = CrewExecutionContext(
            normalized_request=normalized,
            provider=provider,
            orchestration_mode="direct",
        )
        self.stages.generate_initial_output(context)
        self.stages.extract_claims(context, output_key=ORIGINAL_EXTRACTED_CLAIMS)
        self.stages.run_static_analysis(context, output_key=ORIGINAL_STATIC_FINDINGS)
        self.stages.run_sandbox_verification(context, output_key=ORIGINAL_SANDBOX_RESULT)
        self.stages.run_judge(context, output_key=ORIGINAL_JUDGE_RESULT)
        self.stages.run_cove(context, output_key=ORIGINAL_COVE_RESULT)
        self.stages.decide_policy(
            context,
            output_key=ORIGINAL_POLICY_DECISION,
            allow_repair=True,
            target_attempt_key=INITIAL_ATTEMPT,
        )

        if context.initial_attempt is None:
            raise ValueError("Direct execution did not create an initial attempt.")

        if context.initial_attempt.policy_decision.state.value == "repair_and_retry":
            self.stages.generate_repair_output(context)
            self.stages.extract_claims(context, output_key=REPAIR_EXTRACTED_CLAIMS)
            self.stages.run_static_analysis(context, output_key=REPAIR_STATIC_FINDINGS)
            self.stages.run_sandbox_verification(context, output_key=REPAIR_SANDBOX_RESULT)
            self.stages.run_judge(context, output_key=REPAIR_JUDGE_RESULT)
            self.stages.run_cove(context, output_key=REPAIR_COVE_RESULT)
            self.stages.decide_policy(
                context,
                output_key=REPAIR_POLICY_DECISION,
                allow_repair=False,
                target_attempt_key=FINAL_ATTEMPT,
            )

        if context.final_attempt is None:
            raise ValueError("Direct execution did not create a final attempt.")

        context.repair_result = self.stages.build_repair_result(context)
        return ExecutionResult(
            initial_attempt=context.initial_attempt,
            final_attempt=context.final_attempt,
            repair_result=context.repair_result,
            orchestration_trace=[],
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
            orchestration_mode="crewai",
        )
        context = self.runner.run(context, self._build_task_specs())

        if context.initial_attempt is None or context.final_attempt is None:
            raise ValueError("CrewAI execution did not produce a complete run result.")

        context.repair_result = self.stages.build_repair_result(context)
        return ExecutionResult(
            initial_attempt=context.initial_attempt,
            final_attempt=context.final_attempt,
            repair_result=context.repair_result,
            orchestration_trace=context.trace,
        )

    def _build_task_specs(self) -> list[CrewTaskSpec]:
        return [
            CrewTaskSpec(
                name="generate_output",
                stage="generate",
                description="Generate the initial coder output for verification.",
                expected_output="A coder output object ready for verification.",
                agent_role=GENERATOR_AGENT["role"],
                output_key=ORIGINAL_GENERATED_OUTPUT,
                audit_label="original_generation",
                run=self.stages.generate_initial_output,
            ),
            CrewTaskSpec(
                name="extract_claims",
                stage="extract_claims",
                description="Extract structured claims from the generated output.",
                expected_output="A structured list of extracted claims.",
                agent_role=CLAIM_EXTRACTOR_AGENT["role"],
                output_key=ORIGINAL_EXTRACTED_CLAIMS,
                depends_on=(ORIGINAL_GENERATED_OUTPUT,),
                audit_label="original_claims",
                run=lambda context: self.stages.extract_claims(
                    context,
                    output_key=ORIGINAL_EXTRACTED_CLAIMS,
                ),
            ),
            CrewTaskSpec(
                name="static_analysis",
                stage="static_analysis",
                description="Run deterministic syntax and static checks.",
                expected_output="Static findings produced from the generated code.",
                agent_role=STATIC_VERIFIER_AGENT["role"],
                output_key=ORIGINAL_STATIC_FINDINGS,
                depends_on=(ORIGINAL_GENERATED_OUTPUT,),
                audit_label="original_static_analysis",
                run=lambda context: self.stages.run_static_analysis(
                    context,
                    output_key=ORIGINAL_STATIC_FINDINGS,
                ),
            ),
            CrewTaskSpec(
                name="sandbox_verify",
                stage="sandbox_verify",
                description="Run bounded sandbox validation on the generated code.",
                expected_output="A sandbox verification result.",
                agent_role=STATIC_VERIFIER_AGENT["role"],
                output_key=ORIGINAL_SANDBOX_RESULT,
                depends_on=(ORIGINAL_GENERATED_OUTPUT,),
                audit_label="original_sandbox",
                run=lambda context: self.stages.run_sandbox_verification(
                    context,
                    output_key=ORIGINAL_SANDBOX_RESULT,
                ),
            ),
            CrewTaskSpec(
                name="judge_output",
                stage="judge",
                description="Score hallucination risk using the judge stage.",
                expected_output="A judge result with hallucination findings.",
                agent_role=JUDGE_AGENT["role"],
                output_key=ORIGINAL_JUDGE_RESULT,
                depends_on=(
                    ORIGINAL_GENERATED_OUTPUT,
                    ORIGINAL_EXTRACTED_CLAIMS,
                    ORIGINAL_STATIC_FINDINGS,
                    ORIGINAL_SANDBOX_RESULT,
                ),
                audit_label="original_judge",
                run=lambda context: self.stages.run_judge(
                    context,
                    output_key=ORIGINAL_JUDGE_RESULT,
                ),
            ),
            CrewTaskSpec(
                name="cove_output",
                stage="cove",
                description="Re-check extracted claims with the CoVe stage.",
                expected_output="A CoVe result with claim support findings.",
                agent_role=COVE_AGENT["role"],
                output_key=ORIGINAL_COVE_RESULT,
                depends_on=(
                    ORIGINAL_GENERATED_OUTPUT,
                    ORIGINAL_EXTRACTED_CLAIMS,
                    ORIGINAL_STATIC_FINDINGS,
                    ORIGINAL_SANDBOX_RESULT,
                    ORIGINAL_JUDGE_RESULT,
                ),
                audit_label="original_cove",
                run=lambda context: self.stages.run_cove(
                    context,
                    output_key=ORIGINAL_COVE_RESULT,
                ),
            ),
            CrewTaskSpec(
                name="policy_decide",
                stage="policy_decide",
                description="Fuse verification evidence into the first policy decision.",
                expected_output="An initial evaluation bundle with policy decision.",
                agent_role=POLICY_COORDINATOR_AGENT["role"],
                output_key=ORIGINAL_POLICY_DECISION,
                depends_on=(
                    ORIGINAL_STATIC_FINDINGS,
                    ORIGINAL_SANDBOX_RESULT,
                    ORIGINAL_JUDGE_RESULT,
                    ORIGINAL_COVE_RESULT,
                ),
                audit_label="original_policy",
                run=lambda context: self.stages.decide_policy(
                    context,
                    output_key=ORIGINAL_POLICY_DECISION,
                    allow_repair=True,
                    target_attempt_key=INITIAL_ATTEMPT,
                ),
            ),
            CrewTaskSpec(
                name="repair_output",
                stage="repair",
                description="Generate one repair output when policy requests mitigation.",
                expected_output="A repaired coder output ready for re-verification.",
                agent_role=REPAIR_AGENT["role"],
                output_key=REPAIR_GENERATED_OUTPUT,
                depends_on=(INITIAL_ATTEMPT,),
                audit_label="repair_generation",
                should_run=_should_run_repair,
                run=self.stages.generate_repair_output,
            ),
            CrewTaskSpec(
                name="repair_extract_claims",
                stage="extract_claims",
                description="Extract claims from the repaired output.",
                expected_output="A structured list of extracted claims for the repaired output.",
                agent_role=CLAIM_EXTRACTOR_AGENT["role"],
                output_key=REPAIR_EXTRACTED_CLAIMS,
                depends_on=(REPAIR_GENERATED_OUTPUT,),
                audit_label="repair_claims",
                should_run=_should_run_repair_verification,
                run=lambda context: self.stages.extract_claims(
                    context,
                    output_key=REPAIR_EXTRACTED_CLAIMS,
                ),
            ),
            CrewTaskSpec(
                name="repair_static_analysis",
                stage="static_analysis",
                description="Run deterministic syntax and static checks on the repaired output.",
                expected_output="Static findings produced from the repaired code.",
                agent_role=STATIC_VERIFIER_AGENT["role"],
                output_key=REPAIR_STATIC_FINDINGS,
                depends_on=(REPAIR_GENERATED_OUTPUT,),
                audit_label="repair_static_analysis",
                should_run=_should_run_repair_verification,
                run=lambda context: self.stages.run_static_analysis(
                    context,
                    output_key=REPAIR_STATIC_FINDINGS,
                ),
            ),
            CrewTaskSpec(
                name="repair_sandbox_verify",
                stage="sandbox_verify",
                description="Run bounded sandbox validation on the repaired code.",
                expected_output="A sandbox verification result for the repaired output.",
                agent_role=STATIC_VERIFIER_AGENT["role"],
                output_key=REPAIR_SANDBOX_RESULT,
                depends_on=(REPAIR_GENERATED_OUTPUT,),
                audit_label="repair_sandbox",
                should_run=_should_run_repair_verification,
                run=lambda context: self.stages.run_sandbox_verification(
                    context,
                    output_key=REPAIR_SANDBOX_RESULT,
                ),
            ),
            CrewTaskSpec(
                name="repair_judge_output",
                stage="judge",
                description="Score hallucination risk for the repaired output.",
                expected_output="A judge result for the repaired output.",
                agent_role=JUDGE_AGENT["role"],
                output_key=REPAIR_JUDGE_RESULT,
                depends_on=(
                    REPAIR_GENERATED_OUTPUT,
                    REPAIR_EXTRACTED_CLAIMS,
                    REPAIR_STATIC_FINDINGS,
                    REPAIR_SANDBOX_RESULT,
                ),
                audit_label="repair_judge",
                should_run=_should_run_repair_verification,
                run=lambda context: self.stages.run_judge(
                    context,
                    output_key=REPAIR_JUDGE_RESULT,
                ),
            ),
            CrewTaskSpec(
                name="repair_cove_output",
                stage="cove",
                description="Re-check repaired claims with the CoVe stage.",
                expected_output="A CoVe result for the repaired output.",
                agent_role=COVE_AGENT["role"],
                output_key=REPAIR_COVE_RESULT,
                depends_on=(
                    REPAIR_GENERATED_OUTPUT,
                    REPAIR_EXTRACTED_CLAIMS,
                    REPAIR_STATIC_FINDINGS,
                    REPAIR_SANDBOX_RESULT,
                    REPAIR_JUDGE_RESULT,
                ),
                audit_label="repair_cove",
                should_run=_should_run_repair_verification,
                run=lambda context: self.stages.run_cove(
                    context,
                    output_key=REPAIR_COVE_RESULT,
                ),
            ),
            CrewTaskSpec(
                name="repair_policy_decide",
                stage="policy_decide",
                description="Fuse verification evidence into the final policy decision.",
                expected_output="A final evaluation bundle and policy decision.",
                agent_role=POLICY_COORDINATOR_AGENT["role"],
                output_key=REPAIR_POLICY_DECISION,
                depends_on=(
                    REPAIR_STATIC_FINDINGS,
                    REPAIR_SANDBOX_RESULT,
                    REPAIR_JUDGE_RESULT,
                    REPAIR_COVE_RESULT,
                ),
                audit_label="repair_policy",
                should_run=_should_run_repair_verification,
                run=lambda context: self.stages.decide_policy(
                    context,
                    output_key=REPAIR_POLICY_DECISION,
                    allow_repair=False,
                    target_attempt_key=FINAL_ATTEMPT,
                ),
            ),
        ]


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


def _should_run_repair(context: CrewExecutionContext) -> tuple[bool, str | None]:
    if context.initial_attempt is None:
        return False, "Initial attempt is unavailable."
    if context.initial_attempt.policy_decision.state.value != "repair_and_retry":
        return False, "Policy did not request repair."
    return True, None


def _should_run_repair_verification(context: CrewExecutionContext) -> tuple[bool, str | None]:
    if not context.has_artifact(REPAIR_GENERATED_OUTPUT):
        return False, "Repair output was not generated."
    return True, None


def _summarize_repair(original_output: CoderOutput, repaired_output: CoderOutput) -> str:
    if not repaired_output.code.strip():
        return "Repair attempt did not return code."
    if repaired_output.code.strip() == original_output.code.strip():
        return "Repair attempt returned code unchanged."
    return "Repair attempt returned revised code for re-verification."
