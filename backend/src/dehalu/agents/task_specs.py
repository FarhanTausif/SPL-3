"""CrewAI Task Specification Framework for DeHalu Hallucination Detection Pipeline.

This module defines 9 CrewTaskSpec instances that compose the complete verification
and mitigation pipeline. Each task maps to a verification stage in System_Design.md
and coordinates with the orchestration layer defined in execution.py.

Task Hierarchy:
    1. ClarificationTask (optional, pre-generation)
    2. GenerationTask (main code generation)
    3. ClaimExtractionTask (deterministic analysis)
    4. StaticAnalysisTask (deterministic analysis)
    5. SandboxExecutionTask (runtime analysis)
    6. JudgeTask (LLM-based judgment)
    7. CoVeTask (LLM-based Chain-of-Verification)
    8. PolicyCoordinatorTask (deterministic decision fusion)
    9. RepairTask (conditional mitigation)

Dependencies:
    - Clarification → (optional) → Generation
    - Generation → Claims, Static, Sandbox (parallel)
    - Judge depends on (Claims, Static, Sandbox)
    - CoVe depends on (Claims, Judge)
    - Policy depends on (Judge, CoVe)
    - Repair depends on (Policy), conditional execution

All tasks use async/await patterns and are language-agnostic where possible.
"""

from __future__ import annotations

from dehalu.agents.contracts import CrewExecutionContext, CrewTaskSpec
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
from dehalu.orchestration.execution import (
    INITIAL_ATTEMPT,
    ORIGINAL_COVE_RESULT,
    ORIGINAL_EXTRACTED_CLAIMS,
    ORIGINAL_JUDGE_RESULT,
    ORIGINAL_POLICY_DECISION,
    ORIGINAL_SANDBOX_RESULT,
    ORIGINAL_STATIC_FINDINGS,
    ORIGINAL_GENERATED_OUTPUT,
    REPAIR_ATTEMPT,
    REPAIR_COVE_RESULT,
    REPAIR_EXTRACTED_CLAIMS,
    REPAIR_GENERATED_OUTPUT,
    REPAIR_JUDGE_RESULT,
    REPAIR_POLICY_DECISION,
    REPAIR_SANDBOX_RESULT,
    REPAIR_STATIC_FINDINGS,
    _ExecutionStages,
)
from dehalu.schemas import PolicyDecisionState


# =============================================================================
# TASK 1: CLARIFICATION TASK
# =============================================================================
def _clarification_task_should_run(context: CrewExecutionContext) -> tuple[bool, str | None]:
    """Determine if clarification is needed based on request ambiguities.

    Checks for:
    - Missing or None task specification
    - Missing or ambiguous language specification
    - Missing framework or runtime constraints
    - Missing or vague acceptance criteria
    - High-risk requests with underspecified details

    Args:
        context: Execution context with normalized request

    Returns:
        Tuple of (should_run: bool, reason: str | None)
    """
    req = context.normalized_request

    # Check for missing language
    if not req.language or req.language == "unknown":
        return True, "Language specification is ambiguous or missing"

    # Check for missing or vague prompt
    if not req.prompt or len(req.prompt) < 20:
        return True, "Task specification is too brief or unclear"

    # Check for high-risk with missing constraints
    if req.risk_level.value == "high" and not req.acceptance_criteria:
        return True, "High-risk request needs explicit acceptance criteria"

    # Check for missing runtime context
    if not req.target_runtime and req.language in ("go", "rust", "c", "cpp"):
        return True, "Runtime environment not specified for compiled language"

    return False, None


def _run_clarification(context: CrewExecutionContext) -> None:
    """Execute clarification stage.

    Invokes the provider's clarify method to resolve ambiguities in the request.
    Records trace entry and stores clarification result in artifacts.

    Args:
        context: Execution context to populate with clarification result
    """
    clarification_result = context.provider.clarify(context.normalized_request)
    context.set_artifact("clarification.result", clarification_result)
    context.record_trace(
        task_name="ClarificationTask",
        stage="pre_generation",
        agent_role=CLARIFICATION_AGENT["role"],
        status="completed",
        output_key="clarification.result",
        audit_label="clarify_request",
        detail=f"Resolved ambiguities: {', '.join(clarification_result.ambiguity_flags)}",
    )


CLARIFICATION_TASK = CrewTaskSpec(
    name="ClarificationTask",
    stage="pre_generation",
    description=(
        "Detect and resolve ambiguous request specifications before code generation. "
        "Identifies missing constraints (language, framework, runtime), fills in implicit "
        "assumptions, and produces a clarified task spec with explicit acceptance criteria."
    ),
    expected_output=(
        "ClarificationResult with clarified_prompt, language, runtime_assumptions, "
        "constraints, and acceptance_criteria; needs_user_input flag if input required"
    ),
    agent_role=CLARIFICATION_AGENT["role"],
    output_key="clarification.result",
    run=_run_clarification,
    depends_on=(),
    audit_label="clarify_request",
    should_run=_clarification_task_should_run,
)


# =============================================================================
# TASK 2: GENERATION TASK
# =============================================================================
def _generation_task_should_run(context: CrewExecutionContext) -> tuple[bool, str | None]:
    """Determine if generation should run (always true, but for consistency)."""
    return True, None


def _run_generation(context: CrewExecutionContext, stages: _ExecutionStages) -> None:
    """Execute code generation stage.

    Invokes the provider's generate method on the normalized request.
    Stores the generated output and records trace.

    Args:
        context: Execution context to populate with generated output
        stages: Execution stages helper for generation invocation
    """
    stages.generate_initial_output(context)
    context.record_trace(
        task_name="GenerationTask",
        stage="generation",
        agent_role=GENERATOR_AGENT["role"],
        status="completed",
        output_key=ORIGINAL_GENERATED_OUTPUT,
        audit_label="generate_code",
        detail=(
            f"Generated {len(context.generated_output.code)} bytes; "
            f"{len(context.generated_output.assumptions)} assumptions, "
            f"{len(context.generated_output.dependencies)} dependencies"
        ),
    )


def _create_generation_task(stages: _ExecutionStages) -> CrewTaskSpec:
    """Factory to create GenerationTask with stages closure."""

    def run_generation(context: CrewExecutionContext) -> None:
        _run_generation(context, stages)

    return CrewTaskSpec(
        name="GenerationTask",
        stage="generation",
        description=(
            "Generate a single, complete code implementation addressing the normalized task. "
            "Produces syntactically valid code with explicit assumptions and dependencies. "
            "All generated code enters the verification pipeline; no shortcuts."
        ),
        expected_output=(
            "CoderOutput with complete code, dependencies list, assumptions, "
            "execution_notes, and metadata; all required fields populated"
        ),
        agent_role=GENERATOR_AGENT["role"],
        output_key=ORIGINAL_GENERATED_OUTPUT,
        run=run_generation,
        depends_on=("ClarificationTask",),  # Optional dependency via should_run
        audit_label="generate_code",
        should_run=_generation_task_should_run,
    )


# =============================================================================
# TASK 3: CLAIM EXTRACTION TASK
# =============================================================================
def _run_claim_extraction(context: CrewExecutionContext, stages: _ExecutionStages) -> None:
    """Execute deterministic claim extraction stage.

    Uses language-specific adapters and parsing to extract verifiable claims
    from generated code: dependencies, imports, APIs, symbols, assumptions.

    Args:
        context: Execution context to populate with extracted claims
        stages: Execution stages helper for claim extraction
    """
    stages.extract_claims(context, output_key=ORIGINAL_EXTRACTED_CLAIMS)
    context.record_trace(
        task_name="ClaimExtractionTask",
        stage="analysis",
        agent_role=CLAIM_EXTRACTOR_AGENT["role"],
        status="completed",
        output_key=ORIGINAL_EXTRACTED_CLAIMS,
        audit_label="extract_claims",
        detail=f"Extracted {len(context.extracted_claims)} claims for verification",
    )


def _create_claim_extraction_task(stages: _ExecutionStages) -> CrewTaskSpec:
    """Factory to create ClaimExtractionTask with stages closure."""

    def run_claim_extraction(context: CrewExecutionContext) -> None:
        _run_claim_extraction(context, stages)

    return CrewTaskSpec(
        name="ClaimExtractionTask",
        stage="analysis",
        description=(
            "Extract verifiable claims from generated code using language-specific "
            "parsing. Identifies all dependencies, imports, API/symbol references, "
            "runtime assumptions, and promised behaviors as structured claim objects."
        ),
        expected_output=(
            "List of ExtractedClaim objects with kind, value, source, and metadata; "
            "ready for verification against static and runtime evidence"
        ),
        agent_role=CLAIM_EXTRACTOR_AGENT["role"],
        output_key=ORIGINAL_EXTRACTED_CLAIMS,
        run=run_claim_extraction,
        depends_on=("GenerationTask",),
        audit_label="extract_claims",
    )


# =============================================================================
# TASK 4: STATIC ANALYSIS TASK
# =============================================================================
def _run_static_analysis(context: CrewExecutionContext, stages: _ExecutionStages) -> None:
    """Execute deterministic static analysis stage.

    Applies syntax validation, AST parsing, import resolution, symbol verification,
    and unsafe pattern detection using Tree-sitter and language adapters.

    Args:
        context: Execution context to populate with static findings
        stages: Execution stages helper for static analysis
    """
    stages.run_static_analysis(context, output_key=ORIGINAL_STATIC_FINDINGS)
    context.record_trace(
        task_name="StaticAnalysisTask",
        stage="analysis",
        agent_role=STATIC_VERIFIER_AGENT["role"],
        status="completed",
        output_key=ORIGINAL_STATIC_FINDINGS,
        audit_label="static_analysis",
        detail=f"Found {len(context.static_findings)} issues in static analysis",
    )


def _create_static_analysis_task(stages: _ExecutionStages) -> CrewTaskSpec:
    """Factory to create StaticAnalysisTask with stages closure."""

    def run_static_analysis(context: CrewExecutionContext) -> None:
        _run_static_analysis(context, stages)

    return CrewTaskSpec(
        name="StaticAnalysisTask",
        stage="analysis",
        description=(
            "Apply deterministic static checks: syntax validation, AST parsing, "
            "import resolution, symbol verification, and unsafe pattern detection. "
            "Uses Tree-sitter and language-specific adapters; findings are evidence, not verdicts."
        ),
        expected_output=(
            "List of StaticFinding objects with code, message, severity, and location; "
            "includes syntax errors, import issues, undefined symbols, and dangerous patterns"
        ),
        agent_role=STATIC_VERIFIER_AGENT["role"],
        output_key=ORIGINAL_STATIC_FINDINGS,
        run=run_static_analysis,
        depends_on=("GenerationTask",),
        audit_label="static_analysis",
    )


# =============================================================================
# TASK 5: SANDBOX EXECUTION TASK
# =============================================================================
def _run_sandbox_execution(context: CrewExecutionContext, stages: _ExecutionStages) -> None:
    """Execute bounded sandbox verification stage.

    Runs generated code in a containerized, resource-limited environment with
    timeouts and output capture. Validates execution without hallucination.

    Args:
        context: Execution context to populate with sandbox result
        stages: Execution stages helper for sandbox execution
    """
    stages.run_sandbox_verification(context, output_key=ORIGINAL_SANDBOX_RESULT)
    context.record_trace(
        task_name="SandboxExecutionTask",
        stage="analysis",
        agent_role="Sandbox Verifier",
        status="completed",
        output_key=ORIGINAL_SANDBOX_RESULT,
        audit_label="sandbox_execution",
        detail=(
            f"Execution {context.sandbox_result.status}: "
            f"duration {context.sandbox_result.duration_ms}ms"
        ),
    )


def _create_sandbox_execution_task(stages: _ExecutionStages) -> CrewTaskSpec:
    """Factory to create SandboxExecutionTask with stages closure."""

    def run_sandbox_execution(context: CrewExecutionContext) -> None:
        _run_sandbox_execution(context, stages)

    return CrewTaskSpec(
        name="SandboxExecutionTask",
        stage="analysis",
        description=(
            "Execute code in a bounded sandbox environment with resource limits and timeouts. "
            "Validates runtime behavior, captures output/errors, and measures execution metrics. "
            "Provides evidence of execution success or failure."
        ),
        expected_output=(
            "SandboxResult with status (passed/failed/unsupported), duration_ms, "
            "captured output/stderr, findings from execution trace, and metadata"
        ),
        agent_role=STATIC_VERIFIER_AGENT["role"],
        output_key=ORIGINAL_SANDBOX_RESULT,
        run=run_sandbox_execution,
        depends_on=("GenerationTask",),
        audit_label="sandbox_execution",
    )


# =============================================================================
# TASK 6: JUDGE TASK
# =============================================================================
def _run_judge(context: CrewExecutionContext, stages: _ExecutionStages) -> None:
    """Execute LLM-based judgment stage.

    Invokes the provider's judge method with structured inputs to evaluate
    hallucination risk across multiple metrics: requirement alignment, claim
    consistency, dependency plausibility, API validity, execution validity.

    Args:
        context: Execution context to populate with judge result
        stages: Execution stages helper for judge invocation
    """
    stages.run_judge(context, output_key=ORIGINAL_JUDGE_RESULT)
    context.record_trace(
        task_name="JudgeTask",
        stage="judgment",
        agent_role=JUDGE_AGENT["role"],
        status="completed",
        output_key=ORIGINAL_JUDGE_RESULT,
        audit_label="judge_verdict",
        detail=(
            f"Judge verdict: {context.judge_result.verdict}; "
            f"hallucination_score: {context.judge_result.hallucination_score:.2f}"
        ),
    )


def _create_judge_task(stages: _ExecutionStages) -> CrewTaskSpec:
    """Factory to create JudgeTask with stages closure."""

    def run_judge(context: CrewExecutionContext) -> None:
        _run_judge(context, stages)

    return CrewTaskSpec(
        name="JudgeTask",
        stage="judgment",
        description=(
            "Evaluate hallucination risk via LLM-based structured judgment. "
            "Scores requirement alignment, claim consistency, dependency plausibility, "
            "API validity, execution validity, and unsupported assumptions. "
            "Produces verdict and hallucination likelihood score."
        ),
        expected_output=(
            "JudgeResult with verdict (pass/uncertain/fail), hallucination_score (0-1), "
            "findings list with per-metric reasoning, and structured metrics dict"
        ),
        agent_role=JUDGE_AGENT["role"],
        output_key=ORIGINAL_JUDGE_RESULT,
        run=run_judge,
        depends_on=("ClaimExtractionTask", "StaticAnalysisTask", "SandboxExecutionTask"),
        audit_label="judge_verdict",
    )


# =============================================================================
# TASK 7: COVE TASK (Chain-of-Verification)
# =============================================================================
def _run_cove(context: CrewExecutionContext, stages: _ExecutionStages) -> None:
    """Execute Chain-of-Verification (CoVe) stage.

    Independently re-checks each extracted claim against generated code,
    static findings, and sandbox results. Surfacing disagreements with judge.

    Args:
        context: Execution context to populate with CoVe result
        stages: Execution stages helper for CoVe invocation
    """
    stages.run_cove(context, output_key=ORIGINAL_COVE_RESULT)
    context.record_trace(
        task_name="CoVeTask",
        stage="judgment",
        agent_role=COVE_AGENT["role"],
        status="completed",
        output_key=ORIGINAL_COVE_RESULT,
        audit_label="cove_verification",
        detail=(
            f"CoVe verdict: {context.cove_result.verdict}; "
            f"checked {len(context.cove_result.checks)} claims; "
            f"hallucination_score: {context.cove_result.hallucination_score:.2f}"
        ),
    )


def _create_cove_task(stages: _ExecutionStages) -> CrewTaskSpec:
    """Factory to create CoVeTask with stages closure."""

    def run_cove(context: CrewExecutionContext) -> None:
        _run_cove(context, stages)

    return CrewTaskSpec(
        name="CoVeTask",
        stage="judgment",
        description=(
            "Implement Chain-of-Verification (CoVe) by independently re-checking each "
            "extracted claim against generated code and verification evidence. "
            "Identifies supported vs. unsupported claims and surfaces disagreements with judge."
        ),
        expected_output=(
            "CoVeResult with verdict (pass/uncertain/fail), hallucination_score (0-1), "
            "list of CoVeClaimCheck objects (one per claim with supported/uncertain/unsupported), "
            "and findings list with reasoning"
        ),
        agent_role=COVE_AGENT["role"],
        output_key=ORIGINAL_COVE_RESULT,
        run=run_cove,
        depends_on=("ClaimExtractionTask", "JudgeTask"),
        audit_label="cove_verification",
    )


# =============================================================================
# TASK 8: POLICY COORDINATOR TASK
# =============================================================================
def _run_policy_decision(context: CrewExecutionContext, stages: _ExecutionStages) -> None:
    """Execute policy coordination and decision fusion stage.

    Aggregates all verification evidence (static, sandbox, judge, CoVe) into
    a final decision: accept, warn_and_return_partial, repair_and_retry, or reject.

    Args:
        context: Execution context to populate with policy decision
        stages: Execution stages helper for policy decision
    """
    allow_repair = context.attempt_number == 1  # Only allow repair on first attempt
    stages.decide_policy(
        context,
        output_key=ORIGINAL_POLICY_DECISION,
        allow_repair=allow_repair,
        target_attempt_key=INITIAL_ATTEMPT,
    )
    context.record_trace(
        task_name="PolicyCoordinatorTask",
        stage="policy",
        agent_role=POLICY_COORDINATOR_AGENT["role"],
        status="completed",
        output_key=ORIGINAL_POLICY_DECISION,
        audit_label="policy_decision",
        detail=(
            f"Policy decision: {context.policy_decision.state}; "
            f"score: {context.policy_decision.score:.2f}; "
            f"reasons: {', '.join(context.policy_decision.reasons[:2])}"
        ),
    )


def _create_policy_coordinator_task(stages: _ExecutionStages) -> CrewTaskSpec:
    """Factory to create PolicyCoordinatorTask with stages closure."""

    def run_policy_decision(context: CrewExecutionContext) -> None:
        _run_policy_decision(context, stages)

    return CrewTaskSpec(
        name="PolicyCoordinatorTask",
        stage="policy",
        description=(
            "Fuse all verification evidence into a final policy decision. "
            "Aggregates static findings, sandbox results, judge scores, and CoVe reports. "
            "Produces decision: accept (low hallucination), warn_and_return_partial (medium), "
            "repair_and_retry (trigger mitigation), or reject (high/critical)."
        ),
        expected_output=(
            "PolicyDecision with state, reasons list, hard_fail flag, score (0-1), "
            "and metrics dict with repair_trigger if repair_and_retry state"
        ),
        agent_role=POLICY_COORDINATOR_AGENT["role"],
        output_key=ORIGINAL_POLICY_DECISION,
        run=run_policy_decision,
        depends_on=("JudgeTask", "CoVeTask"),
        audit_label="policy_decision",
    )


# =============================================================================
# TASK 9: REPAIR TASK
# =============================================================================
def _repair_task_should_run(context: CrewExecutionContext) -> tuple[bool, str | None]:
    """Determine if repair should run based on policy decision.

    Repair only runs if the initial attempt's policy decision state is
    repair_and_retry.

    Args:
        context: Execution context with policy decision

    Returns:
        Tuple of (should_run: bool, reason: str | None)
    """
    if context.initial_attempt is None:
        return False, "No initial attempt; repair skipped"

    if context.initial_attempt.policy_decision.state == PolicyDecisionState.repair_and_retry:
        trigger = context.initial_attempt.policy_decision.metrics.get(
            "repair_trigger", "unknown"
        )
        return True, f"Repair triggered by: {trigger}"

    return False, "Policy decision does not require repair"


def _run_repair(context: CrewExecutionContext, stages: _ExecutionStages) -> None:
    """Execute repair (mitigation) stage.

    Corrects hallucinated code by addressing specific failures identified
    in the policy decision. Re-runs full verification on repaired output.

    Args:
        context: Execution context to populate with repair output and re-verification
        stages: Execution stages helper for repair flow
    """
    # Generate repaired output
    stages.generate_repair_output(context)
    context.record_trace(
        task_name="RepairTask",
        stage="mitigation",
        agent_role=REPAIR_AGENT["role"],
        status="repaired",
        output_key=REPAIR_GENERATED_OUTPUT,
        audit_label="repair_output",
        detail=(
            f"Repair produced {len(context.generated_output.code)} bytes; "
            f"addressing {len(context.initial_attempt.policy_decision.reasons)} findings"
        ),
    )

    # Re-verify the repaired output
    stages.extract_claims(context, output_key=REPAIR_EXTRACTED_CLAIMS)
    stages.run_static_analysis(context, output_key=REPAIR_STATIC_FINDINGS)
    stages.run_sandbox_verification(context, output_key=REPAIR_SANDBOX_RESULT)
    stages.run_judge(context, output_key=REPAIR_JUDGE_RESULT)
    stages.run_cove(context, output_key=REPAIR_COVE_RESULT)

    # Final policy decision (no more repairs allowed)
    stages.decide_policy(
        context,
        output_key=REPAIR_POLICY_DECISION,
        allow_repair=False,
        target_attempt_key="final_attempt",
    )

    context.record_trace(
        task_name="RepairTask",
        stage="mitigation",
        agent_role=REPAIR_AGENT["role"],
        status="re_verified",
        output_key=REPAIR_POLICY_DECISION,
        audit_label="repair_verification",
        detail=(
            f"Repair verification complete; "
            f"final decision: {context.final_attempt.policy_decision.state}"
        ),
    )

    # Build repair result
    context.repair_result = stages.build_repair_result(context)


def _create_repair_task(stages: _ExecutionStages) -> CrewTaskSpec:
    """Factory to create RepairTask with stages closure."""

    def run_repair(context: CrewExecutionContext) -> None:
        _run_repair(context, stages)

    return CrewTaskSpec(
        name="RepairTask",
        stage="mitigation",
        description=(
            "Correct hallucinated code by addressing specific failures identified in "
            "the policy decision. Produces corrected code that re-enters the full "
            "verification pipeline. No shortcuts—repair output gets same rigor as original."
        ),
        expected_output=(
            "Updated context with: REPAIR_GENERATED_OUTPUT (CoderOutput), "
            "REPAIR_EXTRACTED_CLAIMS, REPAIR_STATIC_FINDINGS, REPAIR_SANDBOX_RESULT, "
            "REPAIR_JUDGE_RESULT, REPAIR_COVE_RESULT, REPAIR_POLICY_DECISION, "
            "and populated repair_result with RepairResult object"
        ),
        agent_role=REPAIR_AGENT["role"],
        output_key=REPAIR_POLICY_DECISION,
        run=run_repair,
        depends_on=("PolicyCoordinatorTask",),
        audit_label="repair_execution",
        should_run=_repair_task_should_run,
    )


# =============================================================================
# FACTORY: CREATE ALL TASK SPECS
# =============================================================================


def create_all_task_specs(stages: _ExecutionStages) -> dict[str, CrewTaskSpec]:
    """Create all 9 CrewTaskSpec instances with execution stages.

    Args:
        stages: _ExecutionStages instance with claim extractor, analyzers, engines

    Returns:
        Dictionary mapping task name to CrewTaskSpec instance
    """
    return {
        "ClarificationTask": CLARIFICATION_TASK,
        "GenerationTask": _create_generation_task(stages),
        "ClaimExtractionTask": _create_claim_extraction_task(stages),
        "StaticAnalysisTask": _create_static_analysis_task(stages),
        "SandboxExecutionTask": _create_sandbox_execution_task(stages),
        "JudgeTask": _create_judge_task(stages),
        "CoVeTask": _create_cove_task(stages),
        "PolicyCoordinatorTask": _create_policy_coordinator_task(stages),
        "RepairTask": _create_repair_task(stages),
    }


def get_task_spec_by_name(
    task_specs: dict[str, CrewTaskSpec], name: str
) -> CrewTaskSpec | None:
    """Retrieve task spec by name.

    Args:
        task_specs: Dictionary from create_all_task_specs()
        name: Task name (e.g., "GenerationTask")

    Returns:
        CrewTaskSpec if found, else None
    """
    return task_specs.get(name)


def get_task_dependencies(
    task_specs: dict[str, CrewTaskSpec], task_name: str
) -> list[str]:
    """Get task dependencies for topological ordering.

    Args:
        task_specs: Dictionary from create_all_task_specs()
        task_name: Task name

    Returns:
        List of dependency task names
    """
    task = get_task_spec_by_name(task_specs, task_name)
    if task is None:
        return []
    return list(task.depends_on)


__all__ = [
    "create_all_task_specs",
    "get_task_spec_by_name",
    "get_task_dependencies",
    "CLARIFICATION_TASK",
]
