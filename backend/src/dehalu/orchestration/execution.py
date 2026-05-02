from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Protocol

from dehalu.adapters.llm import LLMProvider
from dehalu.agents import CrewAIRunner, CrewExecutionContext, CrewTaskSpec, OrchestrationTraceEntry
from dehalu.agents.roles import (
    CLAIM_EXTRACTOR_AGENT,
    CLARIFICATION_AGENT,
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
        """
        Build the CrewAI task specifications for the full verification pipeline.

        Task flow:
        1. clarify_request (optional) - Sharpen ambiguous requests before generation
        2. generate_output - Produce initial code draft
        3. extract_claims - Extract verifiable claims from code
        4. static_analysis - Run deterministic syntax/AST/import checks
        5. sandbox_verify - Run bounded execution probes
        6. judge_output - Score hallucination risk via LLM-as-a-Judge
        7. cove_output - Chain-of-Verification for claim-level checks
        8. policy_decide - Fuse evidence into policy decision
        9. repair_output (conditional) - Fix detected hallucinations
        10-14. repair_* tasks - Re-verify repaired code
        15. repair_policy_decide - Final policy decision
        """
        return [
            CrewTaskSpec(
                name="clarify_request",
                stage="clarify",
                description=(
                    "Analyze the incoming coding request and identify any ambiguous or missing "
                    "constraints before generation. Transform the raw prompt into a normalized task "
                    "specification with explicit language, framework, runtime, and acceptance criteria. "
                    "Flag underspecified requests that require user clarification rather than proceeding "
                    "with assumptions."
                ),
                expected_output=(
                    "A normalized request object with all constraints made explicit, or a clarification "
                    "response indicating what information is missing from the user."
                ),
                agent_role=CLARIFICATION_AGENT["role"],
                output_key=None,  # Clarification modifies the request in-place
                audit_label="clarification",
                # Clarification runs before generation in worker-backed mode only
                should_run=lambda ctx: (False, "clarification_disabled_for_crewai" if ctx.orchestration_mode == "crewai" else "worker_mode_not_implemented"),
                run=lambda ctx: None,  # Placeholder - clarification handled in service.py
            ),
            CrewTaskSpec(
                name="generate_output",
                stage="generate",
                description=(
                    "Generate a single code implementation that addresses the normalized task "
                    "specification. The output must include: (1) complete source code, (2) a list "
                    "of dependencies and imports, (3) explicit assumptions about the runtime "
                    "environment, and (4) notes on any edge cases or limitations. This code will "
                    "undergo rigorous verification, so completeness and correctness are prioritized "
                    "over speed."
                ),
                expected_output=(
                    "A CoderOutput object containing: code (str), dependencies (list), assumptions "
                    "(list), files_touched (list), and execution_notes (str). The code must be "
                    "syntactically valid and aligned with the requested language and framework."
                ),
                agent_role=GENERATOR_AGENT["role"],
                output_key=ORIGINAL_GENERATED_OUTPUT,
                audit_label="original_generation",
                run=self.stages.generate_initial_output,
            ),
            CrewTaskSpec(
                name="extract_claims",
                stage="extract_claims",
                description=(
                    "Parse the generated code and extract all verifiable claims that require "
                    "downstream validation. Claims include: (1) package dependencies and imports, "
                    "(2) API/symbol references (classes, functions, methods), (3) runtime or "
                    "environment assumptions, (4) behavioral promises (what the code claims to do), "
                    "and (5) side effects or external interactions. Each claim becomes a verification "
                    "target for the judge, CoVe, and static analysis stages."
                ),
                expected_output=(
                    "A list of ExtractedClaim objects, each with: claim_type (dependency/api/assumption/behavior), "
                    "claim_text (the specific claim), confidence (0-1), and evidence_location (line numbers)."
                ),
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
                description=(
                    "Apply deterministic static analysis checks using Tree-sitter and language-specific "
                    "adapters. Verify: (1) syntax validity via AST parsing, (2) import resolution "
                    "(detect non-existent packages), (3) symbol validation (undefined variables/functions), "
                    "(4) unsafe pattern detection (eval, exec, shell injection risks), and (5) language-specific "
                    "linting rules. Static analysis provides hard-fail signals that override prompt-based "
                    "confidence."
                ),
                expected_output=(
                    "A list of StaticFinding objects, each with: finding_type (syntax/import/symbol/safety), "
                    "severity (error/warning/info), message (human-readable description), line_number, "
                    "and code_snippet. Empty list means all static checks passed."
                ),
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
                description=(
                    "Execute bounded runtime probes on the generated code in an isolated sandbox. "
                    "Checks include: (1) compilation/parse check, (2) smoke-run execution, (3) generated "
                    "assertion probes, and (4) metamorphic tests for invariant-preserving transformations. "
                    "The sandbox enforces strict resource limits: CPU, memory, timeout, filesystem, and "
                    "network isolation. Execution failure is a stronger signal than prompt confidence."
                ),
                expected_output=(
                    "A SandboxResult object with: executed (bool), exit_code (int), stdout/stderr (str), "
                    "duration_ms (float), resource_limits (dict), and any exception details. A successful "
                    "execution does not guarantee correctness, but failure strongly indicates hallucination."
                ),
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
                description=(
                    "Evaluate hallucination risk using LLM-as-a-Judge methodology. Score the generated "
                    "code against multiple metrics: (1) requirement_alignment_score - does it solve the "
                    "requested task, (2) claim_consistency_score - do the claims match the code, "
                    "(3) dependency_plausibility_score - are packages/imports real and appropriate, "
                    "(4) api_symbol_validity_score - are referenced APIs real, (5) unsupported_assumption_score "
                    "- what claims lack evidence. The judge receives all deterministic findings and must "
                    "produce a structured verdict, not free-form critique."
                ),
                expected_output=(
                    "A JudgeResult object with: hallucination_likelihood (0-1), metric_scores (dict of "
                    "individual scores), hard_fail_flags (list of critical issues), claim_level_findings "
                    "(list of per-claim verdicts), and overall_verdict (accept/warn/reject with explanation)."
                ),
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
                description=(
                    "Perform Chain-of-Verification (CoVe) by independently re-checking each extracted "
                    "claim against the generated code. For each claim: (1) locate the relevant code "
                    "region, (2) verify the claim is actually supported by the code, (3) flag any "
                    "contradictions between the claim and the code behavior, and (4) mark claims as "
                    "supported/unsupported/uncertain. CoVe provides claim-level granularity that "
                    "complements the judge's holistic assessment."
                ),
                expected_output=(
                    "A CoVeResult object with: claim_checks (list of per-claim verdicts with support "
                    "status and evidence), unsupported_claims_summary (list of flagged claims), "
                    "uncertainty_flags (list of claims that couldn't be verified), and overall_consistency "
                    "score (0-1)."
                ),
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
                description=(
                    "Fuse all verification evidence into a final policy decision. The policy engine "
                    "aggregates: (1) static analysis findings (hard-fail errors), (2) sandbox execution "
                    "results (runtime failures), (3) judge hallucination scores, (4) CoVe claim-level "
                    "verdicts, and (5) task risk level. Based on fused evidence, return one of: "
                    "'accept' (release code), 'warn_and_return_partial' (release with caveats), "
                    "'repair_and_retry' (trigger Fixer Agent), or 'reject' (fail closed with evidence)."
                ),
                expected_output=(
                    "A PolicyDecision object with: state (accept/warn_and_return_partial/repair_and_retry/reject), "
                    "metrics (dict of all scores that influenced the decision), explanation (human-readable "
                    "justification), and repair_trigger (reason if repair was triggered)."
                ),
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
                description=(
                    "Repair the generated code when the policy engine detects hallucination and triggers "
                    "repair-and-retry. The Repair Agent receives: (1) original code, (2) policy decision "
                    "with specific failure reasons, (3) judge findings (flagged hallucinations), "
                    "(4) CoVe report (unsupported claims), and (5) static/sandbox failures. The repair "
                    "must address flagged issues while preserving original intent. May use MCP-backed "
                    "tools for documentation lookup, symbol validation, or dependency resolution."
                ),
                expected_output=(
                    "A CoderOutput object containing repaired code that addresses all flagged hallucinations. "
                    "The output includes the same structure as the original generation: code, dependencies, "
                    "assumptions, and execution notes. A RepairAttempt record is created to track what "
                    "changed and why."
                ),
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
                description=(
                    "Extract claims from the repaired code using the same extraction logic as the "
                    "original pass. This ensures the repaired code's claims are verified downstream. "
                    "Compare extracted claims against the original to detect if repair introduced "
                    "new assumptions or dependencies."
                ),
                expected_output=(
                    "A list of ExtractedClaim objects for the repaired code, ready for verification."
                ),
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
                description=(
                    "Run static analysis on the repaired code to verify that repairs didn't introduce "
                    "new syntax errors, invalid imports, or undefined symbols. The same deterministic "
                    "checks apply: syntax validity, import resolution, symbol validation, and safety "
                    "pattern detection."
                ),
                expected_output=(
                    "A list of StaticFinding objects for the repaired code. Empty list means all "
                    "static checks passed."
                ),
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
                description=(
                    "Execute bounded runtime probes on the repaired code. Verify that the repair "
                    "didn't break execution and that previously failing tests now pass. Same sandbox "
                    "constraints apply: CPU, memory, timeout, filesystem, and network isolation."
                ),
                expected_output=(
                    "A SandboxResult object for the repaired code showing execution success or failure."
                ),
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
                description=(
                    "Re-evaluate hallucination risk for the repaired code. The judge assesses whether "
                    "the repair successfully addressed the flagged issues without introducing new "
                    "hallucinations. Same metrics apply: requirement alignment, claim consistency, "
                    "dependency plausibility, API validity, and unsupported assumptions."
                ),
                expected_output=(
                    "A JudgeResult object for the repaired code with updated hallucination scores "
                    "and verdict."
                ),
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
                description=(
                    "Re-check claims from the repaired code using Chain-of-Verification. Verify that "
                    "previously unsupported claims are now supported and that no new unsupported "
                    "claims were introduced. The CoVe pass on repaired code is critical for ensuring "
                    "repair quality."
                ),
                expected_output=(
                    "A CoVeResult object for the repaired code showing claim-level support status."
                ),
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
                description=(
                    "Make the final policy decision on the repaired code. This is the last chance "
                    "to catch hallucinations before release. The policy engine fuses all re-verification "
                    "evidence and returns: 'accept' (release repaired code), 'warn_and_return_partial' "
                    "(release with caveats), or 'reject' (fail closed with full evidence). Note: "
                    "allow_repair=False, so even if issues persist, no further repair is attempted."
                ),
                expected_output=(
                    "A PolicyDecision object with the final release decision. This decision is "
                    "terminal for the run."
                ),
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
