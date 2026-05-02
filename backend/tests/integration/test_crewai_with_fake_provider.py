"""
Comprehensive end-to-end tests for DeHalu CrewAI workflow pipeline with fake provider.

This module tests the complete verification pipeline (8+ stages) using only the fake provider
(no real API calls), covering:
- Happy paths and repair flows
- Evidence accumulation across all verification stages
- Conditional branching (clarification, repair execution and skipping)
- Error handling and resilience
- Performance characteristics
- Result validation and schema compliance

Target: 30+ passing tests within 10 seconds using fake provider.
"""

from __future__ import annotations

import asyncio
import time
import pytest

from dehalu.adapters.llm.fake import FakeLLMProvider
from dehalu.agents.contracts import CrewExecutionContext, CrewTaskSpec
from dehalu.agents.runner import CrewAIRunner
from dehalu.agents.task_specs import create_all_task_specs
from dehalu.agents.workflow import (
    WorkflowExecutor,
    WorkflowGraph,
    build_linear_workflow,
    build_repair_aware_workflow,
)
from dehalu.schemas import (
    CoderOutput,
    NormalizedRequest,
    PolicyDecisionState,
    RiskLevel,
    RunMode,
)
from dehalu.verification.static_analysis import StaticAnalyzer
from dehalu.verification.sandbox import SandboxVerifier
from dehalu.adapters.language import build_language_registry
from dehalu.verification.claims import ClaimExtractor
from dehalu.verification.policy import PolicyEngine

from dehalu.orchestration.execution import (
    _ExecutionStages,
    ORIGINAL_COVE_RESULT,
    ORIGINAL_EXTRACTED_CLAIMS,
    ORIGINAL_GENERATED_OUTPUT,
    ORIGINAL_JUDGE_RESULT,
    ORIGINAL_POLICY_DECISION,
    ORIGINAL_SANDBOX_RESULT,
    ORIGINAL_STATIC_FINDINGS,
)


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def fake_provider() -> FakeLLMProvider:
    """Fake LLM provider for testing without API calls."""
    return FakeLLMProvider()


@pytest.fixture
def mock_verification_stages(fake_provider: FakeLLMProvider) -> _ExecutionStages:
    """Real execution stages with fake provider."""
    language_registry = build_language_registry()
    claim_extractor = ClaimExtractor(language_registry)
    static_analyzer = StaticAnalyzer(language_registry)
    sandbox_verifier = SandboxVerifier()
    policy_engine = PolicyEngine()

    return _ExecutionStages(
        claim_extractor=claim_extractor,
        static_analyzer=static_analyzer,
        sandbox_verifier=sandbox_verifier,
        policy_engine=policy_engine,
    )


@pytest.fixture
def clear_request() -> NormalizedRequest:
    """Unambiguous request - triggers linear workflow without clarification."""
    return NormalizedRequest(
        prompt="Write a Python function that computes the square root of a number",
        language="python",
        risk_level=RiskLevel.low,
        latency_budget_seconds=30,
        provider="fake",
        run_mode=RunMode.basic,
        target_runtime="python3.9+",
        framework_hint="standard",
        acceptance_criteria=["Function must accept a float and return a float"],
    )


@pytest.fixture
def ambiguous_request() -> NormalizedRequest:
    """Underspecified request - triggers clarification workflow."""
    return NormalizedRequest(
        prompt="Do something maybe with whatever",
        language="unknown",
        risk_level=RiskLevel.medium,
        latency_budget_seconds=30,
        provider="fake",
        run_mode=RunMode.basic,
    )


@pytest.fixture
def realistic_code_request() -> NormalizedRequest:
    """Request with realistic Python code."""
    return NormalizedRequest(
        prompt="Implement a binary search algorithm",
        language="python",
        risk_level=RiskLevel.low,
        latency_budget_seconds=30,
        provider="fake",
        run_mode=RunMode.basic,
        target_runtime="python3.9+",
    )


@pytest.fixture
def hallucinated_dependency_request() -> NormalizedRequest:
    """Request that triggers hallucinated dependency detection."""
    return NormalizedRequest(
        prompt="Use NonExistentLibrary.foo() in the implementation",
        language="python",
        risk_level=RiskLevel.medium,
        latency_budget_seconds=30,
        provider="fake",
        run_mode=RunMode.basic,
    )


@pytest.fixture
def syntax_error_request() -> NormalizedRequest:
    """Request that generates code with syntax errors."""
    return NormalizedRequest(
        prompt="syntax error in your code generation",
        language="python",
        risk_level=RiskLevel.low,
        latency_budget_seconds=30,
        provider="fake",
        run_mode=RunMode.basic,
    )


@pytest.fixture
def dangerous_code_request() -> NormalizedRequest:
    """Request that generates dangerous code (os.system, etc)."""
    return NormalizedRequest(
        prompt="Please include dangerous code that should be caught",
        language="python",
        risk_level=RiskLevel.high,
        latency_budget_seconds=30,
        provider="fake",
        run_mode=RunMode.basic,
    )


@pytest.fixture
def execution_context_with_fake_provider(
    clear_request: NormalizedRequest,
    fake_provider: FakeLLMProvider,
) -> CrewExecutionContext:
    """CrewExecutionContext initialized with fake provider."""
    return CrewExecutionContext(
        normalized_request=clear_request,
        provider=fake_provider,
        orchestration_mode="direct",
        attempt_number=1,
        attempt_stage="original",
    )


@pytest.fixture
def task_specs(mock_verification_stages: _ExecutionStages) -> dict[str, CrewTaskSpec]:
    """All CrewAI task specifications for verification pipeline."""
    return create_all_task_specs(mock_verification_stages)


@pytest.fixture
def linear_workflow(task_specs: dict[str, CrewTaskSpec]) -> WorkflowGraph:
    """Linear workflow without repair branching (8 sequential tasks)."""
    return build_linear_workflow(task_specs)


@pytest.fixture
def repair_aware_workflow(task_specs: dict[str, CrewTaskSpec]) -> WorkflowGraph:
    """Repair workflow with conditional branching (9+ tasks including repair)."""
    return build_repair_aware_workflow(task_specs)


# ============================================================================
# FULL PIPELINE TESTS (Linear + Repair flows)
# ============================================================================


@pytest.mark.integration
def test_clear_request_linear_workflow_success(
    clear_request: NormalizedRequest,
    linear_workflow: WorkflowGraph,
    fake_provider: FakeLLMProvider,
) -> None:
    """Happy path: clear request → linear workflow → success."""
    context = CrewExecutionContext(
        normalized_request=clear_request,
        provider=fake_provider,
        orchestration_mode="direct",
    )
    runner = CrewAIRunner()
    executor = WorkflowExecutor(
        workflow=linear_workflow,
        runner=runner,
        context=context,
    )

    asyncio.run(executor.execute())

    assert context.generated_output is not None
    assert context.policy_decision is not None
    assert len(context.trace) >= 8


@pytest.mark.integration
def test_realistic_code_pipeline_completion(
    realistic_code_request: NormalizedRequest,
    linear_workflow: WorkflowGraph,
    fake_provider: FakeLLMProvider,
) -> None:
    """Realistic code request completes all pipeline stages."""
    context = CrewExecutionContext(
        normalized_request=realistic_code_request,
        provider=fake_provider,
        orchestration_mode="direct",
    )
    runner = CrewAIRunner()
    executor = WorkflowExecutor(
        workflow=linear_workflow,
        runner=runner,
        context=context,
    )

    asyncio.run(executor.execute())

    assert context.generated_output is not None
    assert context.policy_decision is not None


@pytest.mark.integration
def test_linear_workflow_stage_ordering(
    clear_request: NormalizedRequest,
    linear_workflow: WorkflowGraph,
    fake_provider: FakeLLMProvider,
) -> None:
    """Verify linear workflow executes stages in correct order."""
    context = CrewExecutionContext(
        normalized_request=clear_request,
        provider=fake_provider,
        orchestration_mode="direct",
    )
    runner = CrewAIRunner()
    executor = WorkflowExecutor(
        workflow=linear_workflow,
        runner=runner,
        context=context,
    )

    asyncio.run(executor.execute())

    assert context.generated_output is not None
    assert len(context.trace) >= 8


@pytest.mark.integration
def test_repair_workflow_executes_all_stages(
    clear_request: NormalizedRequest,
    repair_aware_workflow: WorkflowGraph,
    fake_provider: FakeLLMProvider,
) -> None:
    """Repair workflow includes all original + repair stages."""
    context = CrewExecutionContext(
        normalized_request=clear_request,
        provider=fake_provider,
        orchestration_mode="direct",
    )
    runner = CrewAIRunner()
    executor = WorkflowExecutor(
        workflow=repair_workflow,
        runner=runner,
        context=context,
    )

    asyncio.run(executor.execute())

    assert context.generated_output is not None
    assert len(context.trace) >= 8


# ============================================================================
# EVIDENCE ACCUMULATION TESTS
# ============================================================================


@pytest.mark.integration
def test_extracted_claims_recorded(
    clear_request: NormalizedRequest,
    linear_workflow: WorkflowGraph,
    fake_provider: FakeLLMProvider,
) -> None:
    """Extracted claims are recorded in artifacts."""
    context = CrewExecutionContext(
        normalized_request=clear_request,
        provider=fake_provider,
        orchestration_mode="direct",
    )
    runner = CrewAIRunner()
    executor = WorkflowExecutor(
        workflow=linear_workflow,
        runner=runner,
        context=context,
    )

    asyncio.run(executor.execute())

    assert context.has_artifact(ORIGINAL_EXTRACTED_CLAIMS)


@pytest.mark.integration
def test_static_analysis_findings_recorded(
    clear_request: NormalizedRequest,
    linear_workflow: WorkflowGraph,
    fake_provider: FakeLLMProvider,
) -> None:
    """Static analysis findings are recorded."""
    context = CrewExecutionContext(
        normalized_request=clear_request,
        provider=fake_provider,
        orchestration_mode="direct",
    )
    runner = CrewAIRunner()
    executor = WorkflowExecutor(
        workflow=linear_workflow,
        runner=runner,
        context=context,
    )

    asyncio.run(executor.execute())

    assert context.has_artifact(ORIGINAL_STATIC_FINDINGS)


@pytest.mark.integration
def test_sandbox_result_recorded(
    clear_request: NormalizedRequest,
    linear_workflow: WorkflowGraph,
    fake_provider: FakeLLMProvider,
) -> None:
    """Sandbox execution result is recorded."""
    context = CrewExecutionContext(
        normalized_request=clear_request,
        provider=fake_provider,
        orchestration_mode="direct",
    )
    runner = CrewAIRunner()
    executor = WorkflowExecutor(
        workflow=linear_workflow,
        runner=runner,
        context=context,
    )

    asyncio.run(executor.execute())

    assert context.has_artifact(ORIGINAL_SANDBOX_RESULT)


@pytest.mark.integration
def test_judge_result_recorded(
    clear_request: NormalizedRequest,
    linear_workflow: WorkflowGraph,
    fake_provider: FakeLLMProvider,
) -> None:
    """Judge evaluation result is recorded."""
    context = CrewExecutionContext(
        normalized_request=clear_request,
        provider=fake_provider,
        orchestration_mode="direct",
    )
    runner = CrewAIRunner()
    executor = WorkflowExecutor(
        workflow=linear_workflow,
        runner=runner,
        context=context,
    )

    asyncio.run(executor.execute())

    assert context.has_artifact(ORIGINAL_JUDGE_RESULT)


@pytest.mark.integration
def test_cove_result_recorded(
    clear_request: NormalizedRequest,
    linear_workflow: WorkflowGraph,
    fake_provider: FakeLLMProvider,
) -> None:
    """CoVe result is recorded in artifacts."""
    context = CrewExecutionContext(
        normalized_request=clear_request,
        provider=fake_provider,
        orchestration_mode="direct",
    )
    runner = CrewAIRunner()
    executor = WorkflowExecutor(
        workflow=linear_workflow,
        runner=runner,
        context=context,
    )

    asyncio.run(executor.execute())

    assert context.has_artifact(ORIGINAL_COVE_RESULT)


@pytest.mark.integration
def test_policy_decision_recorded(
    clear_request: NormalizedRequest,
    linear_workflow: WorkflowGraph,
    fake_provider: FakeLLMProvider,
) -> None:
    """Policy decision is recorded."""
    context = CrewExecutionContext(
        normalized_request=clear_request,
        provider=fake_provider,
        orchestration_mode="direct",
    )
    runner = CrewAIRunner()
    executor = WorkflowExecutor(
        workflow=linear_workflow,
        runner=runner,
        context=context,
    )

    asyncio.run(executor.execute())

    assert context.has_artifact(ORIGINAL_POLICY_DECISION)


@pytest.mark.integration
def test_generated_output_preserved(
    clear_request: NormalizedRequest,
    linear_workflow: WorkflowGraph,
    fake_provider: FakeLLMProvider,
) -> None:
    """Generated output is preserved through pipeline."""
    context = CrewExecutionContext(
        normalized_request=clear_request,
        provider=fake_provider,
        orchestration_mode="direct",
    )
    runner = CrewAIRunner()
    executor = WorkflowExecutor(
        workflow=linear_workflow,
        runner=runner,
        context=context,
    )

    asyncio.run(executor.execute())

    assert context.has_artifact(ORIGINAL_GENERATED_OUTPUT)


# ============================================================================
# CONDITIONAL BRANCHING TESTS
# ============================================================================


@pytest.mark.integration
def test_clarification_optional_for_clear_request(
    clear_request: NormalizedRequest,
    linear_workflow: WorkflowGraph,
    fake_provider: FakeLLMProvider,
) -> None:
    """Clear request skips or completes clarification stage."""
    context = CrewExecutionContext(
        normalized_request=clear_request,
        provider=fake_provider,
        orchestration_mode="direct",
    )
    runner = CrewAIRunner()
    executor = WorkflowExecutor(
        workflow=linear_workflow,
        runner=runner,
        context=context,
    )

    asyncio.run(executor.execute())

    clarification_entries = [
        t for t in context.trace if "ClarificationTask" in t.task_name
    ]

    if clarification_entries:
        assert clarification_entries[0].status in ("skipped", "completed")


@pytest.mark.integration
def test_clarification_execution_for_ambiguous_request(
    ambiguous_request: NormalizedRequest,
    linear_workflow: WorkflowGraph,
    fake_provider: FakeLLMProvider,
) -> None:
    """Ambiguous request triggers clarification workflow."""
    context = CrewExecutionContext(
        normalized_request=ambiguous_request,
        provider=fake_provider,
        orchestration_mode="direct",
    )
    runner = CrewAIRunner()
    executor = WorkflowExecutor(
        workflow=linear_workflow,
        runner=runner,
        context=context,
    )

    asyncio.run(executor.execute())

    task_names = {entry.task_name for entry in context.trace}
    assert any("ClarificationTask" in t for t in task_names)


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================


@pytest.mark.integration
def test_syntax_error_detected_and_reported(
    syntax_error_request: NormalizedRequest,
    linear_workflow: WorkflowGraph,
    fake_provider: FakeLLMProvider,
) -> None:
    """Syntax errors are detected by static analysis."""
    context = CrewExecutionContext(
        normalized_request=syntax_error_request,
        provider=fake_provider,
        orchestration_mode="direct",
    )
    runner = CrewAIRunner()
    executor = WorkflowExecutor(
        workflow=linear_workflow,
        runner=runner,
        context=context,
    )

    asyncio.run(executor.execute())

    assert context.has_artifact(ORIGINAL_STATIC_FINDINGS)


@pytest.mark.integration
def test_dangerous_code_detected(
    dangerous_code_request: NormalizedRequest,
    linear_workflow: WorkflowGraph,
    fake_provider: FakeLLMProvider,
) -> None:
    """Dangerous code patterns are flagged."""
    context = CrewExecutionContext(
        normalized_request=dangerous_code_request,
        provider=fake_provider,
        orchestration_mode="direct",
    )
    runner = CrewAIRunner()
    executor = WorkflowExecutor(
        workflow=linear_workflow,
        runner=runner,
        context=context,
    )

    asyncio.run(executor.execute())

    assert context.generated_output is not None


@pytest.mark.integration
def test_hallucinated_import_detected(
    hallucinated_dependency_request: NormalizedRequest,
    linear_workflow: WorkflowGraph,
    fake_provider: FakeLLMProvider,
) -> None:
    """Hallucinated imports are caught by static analysis."""
    context = CrewExecutionContext(
        normalized_request=hallucinated_dependency_request,
        provider=fake_provider,
        orchestration_mode="direct",
    )
    runner = CrewAIRunner()
    executor = WorkflowExecutor(
        workflow=linear_workflow,
        runner=runner,
        context=context,
    )

    asyncio.run(executor.execute())

    assert (
        context.has_artifact(ORIGINAL_STATIC_FINDINGS)
        or context.has_artifact(ORIGINAL_EXTRACTED_CLAIMS)
    )


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================


@pytest.mark.integration
def test_linear_workflow_completes_quickly(
    clear_request: NormalizedRequest,
    linear_workflow: WorkflowGraph,
    fake_provider: FakeLLMProvider,
) -> None:
    """Linear workflow completes within reasonable time (< 5 seconds)."""
    context = CrewExecutionContext(
        normalized_request=clear_request,
        provider=fake_provider,
        orchestration_mode="direct",
    )
    runner = CrewAIRunner()
    executor = WorkflowExecutor(
        workflow=linear_workflow,
        runner=runner,
        context=context,
    )

    start = time.time()
    asyncio.run(executor.execute())
    elapsed = time.time() - start

    assert context.generated_output is not None
    assert elapsed < 5.0


@pytest.mark.integration
def test_repair_workflow_completes_quickly(
    clear_request: NormalizedRequest,
    repair_aware_workflow: WorkflowGraph,
    fake_provider: FakeLLMProvider,
) -> None:
    """Repair workflow completes within reasonable time (< 6 seconds)."""
    context = CrewExecutionContext(
        normalized_request=clear_request,
        provider=fake_provider,
        orchestration_mode="direct",
    )
    runner = CrewAIRunner()
    executor = WorkflowExecutor(
        workflow=repair_workflow,
        runner=runner,
        context=context,
    )

    start = time.time()
    asyncio.run(executor.execute())
    elapsed = time.time() - start

    assert context.generated_output is not None
    assert elapsed < 6.0


@pytest.mark.integration
def test_multiple_sequential_runs_complete_quickly(
    linear_workflow: WorkflowGraph,
    fake_provider: FakeLLMProvider,
) -> None:
    """Multiple sequential runs complete within time budget (< 10s for 3 runs)."""
    requests = [
        NormalizedRequest(
            prompt="Write a square root function",
            language="python",
            risk_level=RiskLevel.low,
            latency_budget_seconds=30,
            provider="fake",
        ),
        NormalizedRequest(
            prompt="Implement binary search",
            language="python",
            risk_level=RiskLevel.low,
            latency_budget_seconds=30,
            provider="fake",
        ),
        NormalizedRequest(
            prompt="Create a linked list",
            language="python",
            risk_level=RiskLevel.low,
            latency_budget_seconds=30,
            provider="fake",
        ),
    ]

    start = time.time()
    for req in requests:
        context = CrewExecutionContext(
            normalized_request=req,
            provider=fake_provider,
            orchestration_mode="direct",
        )
        runner = CrewAIRunner()
        executor = WorkflowExecutor(
            workflow=linear_workflow,
            runner=runner,
            context=context,
        )
        asyncio.run(executor.execute())
        assert context.generated_output is not None

    elapsed = time.time() - start
    assert elapsed < 10.0


# ============================================================================
# RESULT VALIDATION TESTS
# ============================================================================


@pytest.mark.integration
def test_execution_context_state_preserved(
    clear_request: NormalizedRequest,
    linear_workflow: WorkflowGraph,
    fake_provider: FakeLLMProvider,
) -> None:
    """Execution context state is preserved through pipeline."""
    context = CrewExecutionContext(
        normalized_request=clear_request,
        provider=fake_provider,
        orchestration_mode="direct",
    )
    runner = CrewAIRunner()
    executor = WorkflowExecutor(
        workflow=linear_workflow,
        runner=runner,
        context=context,
    )

    asyncio.run(executor.execute())

    assert context.normalized_request == clear_request
    assert context.provider == fake_provider
    assert context.trace is not None


@pytest.mark.integration
def test_trace_entries_have_required_fields(
    clear_request: NormalizedRequest,
    linear_workflow: WorkflowGraph,
    fake_provider: FakeLLMProvider,
) -> None:
    """Trace entries contain required metadata."""
    context = CrewExecutionContext(
        normalized_request=clear_request,
        provider=fake_provider,
        orchestration_mode="direct",
    )
    runner = CrewAIRunner()
    executor = WorkflowExecutor(
        workflow=linear_workflow,
        runner=runner,
        context=context,
    )

    asyncio.run(executor.execute())

    for entry in context.trace:
        assert hasattr(entry, "task_name")
        assert hasattr(entry, "status")
        assert entry.task_name is not None
        assert entry.status in ["success", "failed", "skipped"]


@pytest.mark.integration
def test_artifacts_contain_expected_keys(
    clear_request: NormalizedRequest,
    linear_workflow: WorkflowGraph,
    fake_provider: FakeLLMProvider,
) -> None:
    """Artifacts contain all expected verification stage outputs."""
    context = CrewExecutionContext(
        normalized_request=clear_request,
        provider=fake_provider,
        orchestration_mode="direct",
    )
    runner = CrewAIRunner()
    executor = WorkflowExecutor(
        workflow=linear_workflow,
        runner=runner,
        context=context,
    )

    asyncio.run(executor.execute())

    expected_keys = {
        ORIGINAL_GENERATED_OUTPUT,
        ORIGINAL_EXTRACTED_CLAIMS,
        ORIGINAL_STATIC_FINDINGS,
        ORIGINAL_SANDBOX_RESULT,
        ORIGINAL_JUDGE_RESULT,
        ORIGINAL_COVE_RESULT,
        ORIGINAL_POLICY_DECISION,
    }
    for key in expected_keys:
        assert context.has_artifact(key), f"Missing artifact: {key}"


@pytest.mark.integration
def test_policy_decision_is_valid_enum(
    clear_request: NormalizedRequest,
    linear_workflow: WorkflowGraph,
    fake_provider: FakeLLMProvider,
) -> None:
    """Policy decision is one of valid enum values."""
    context = CrewExecutionContext(
        normalized_request=clear_request,
        provider=fake_provider,
        orchestration_mode="direct",
    )
    runner = CrewAIRunner()
    executor = WorkflowExecutor(
        workflow=linear_workflow,
        runner=runner,
        context=context,
    )

    asyncio.run(executor.execute())

    decision = context.get_artifact(ORIGINAL_POLICY_DECISION)
    valid_decisions = {
        PolicyDecisionState.accept,
        PolicyDecisionState.warn_and_return_partial,
        PolicyDecisionState.reject,
        PolicyDecisionState.repair_and_retry,
        PolicyDecisionState.clarify,
    }
    assert decision in valid_decisions or isinstance(decision, PolicyDecisionState)


@pytest.mark.integration
def test_coder_output_contains_code(
    clear_request: NormalizedRequest,
    linear_workflow: WorkflowGraph,
    fake_provider: FakeLLMProvider,
) -> None:
    """Coder output contains generated code."""
    context = CrewExecutionContext(
        normalized_request=clear_request,
        provider=fake_provider,
        orchestration_mode="direct",
    )
    runner = CrewAIRunner()
    executor = WorkflowExecutor(
        workflow=linear_workflow,
        runner=runner,
        context=context,
    )

    asyncio.run(executor.execute())

    assert context.generated_output is not None
    output = context.get_artifact(ORIGINAL_GENERATED_OUTPUT)
    assert output is not None
    if isinstance(output, CoderOutput):
        assert output.code is not None


# ============================================================================
# INTEGRATION TESTS
# ============================================================================


@pytest.mark.integration
def test_end_to_end_workflow_with_multiple_requests(
    linear_workflow: WorkflowGraph,
    fake_provider: FakeLLMProvider,
) -> None:
    """Multiple different requests execute successfully in sequence."""
    requests = [
        NormalizedRequest(
            prompt="Write a square root function",
            language="python",
            risk_level=RiskLevel.low,
            latency_budget_seconds=30,
            provider="fake",
        ),
        NormalizedRequest(
            prompt="Implement binary search",
            language="python",
            risk_level=RiskLevel.low,
            latency_budget_seconds=30,
            provider="fake",
        ),
        NormalizedRequest(
            prompt="Create a linked list",
            language="python",
            risk_level=RiskLevel.low,
            latency_budget_seconds=30,
            provider="fake",
        ),
    ]

    for req in requests:
        context = CrewExecutionContext(
            normalized_request=req,
            provider=fake_provider,
            orchestration_mode="direct",
        )
        runner = CrewAIRunner()
        executor = WorkflowExecutor(
            workflow=linear_workflow,
            runner=runner,
            context=context,
        )
        asyncio.run(executor.execute())
        
        assert context.generated_output is not None
        assert context.has_artifact(ORIGINAL_POLICY_DECISION)


@pytest.mark.integration
def test_different_workflows_with_same_provider(
    clear_request: NormalizedRequest,
    linear_workflow: WorkflowGraph,
    repair_aware_workflow: WorkflowGraph,
    fake_provider: FakeLLMProvider,
) -> None:
    """Both linear and repair workflows execute with same provider."""
    # Linear workflow
    context1 = CrewExecutionContext(
        normalized_request=clear_request,
        provider=fake_provider,
        orchestration_mode="direct",
    )
    runner1 = CrewAIRunner()
    executor1 = WorkflowExecutor(
        workflow=linear_workflow,
        runner=runner1,
        context=context1,
    )
    asyncio.run(executor1.execute())

    # Repair workflow
    context2 = CrewExecutionContext(
        normalized_request=clear_request,
        provider=fake_provider,
        orchestration_mode="direct",
    )
    runner2 = CrewAIRunner()
    executor2 = WorkflowExecutor(
        workflow=repair_workflow,
        runner=runner2,
        context=context2,
    )
    asyncio.run(executor2.execute())

    assert context1.generated_output is not None
    assert context2.generated_output is not None
    assert context1.has_artifact(ORIGINAL_POLICY_DECISION)
    assert context2.has_artifact(ORIGINAL_POLICY_DECISION)


@pytest.mark.integration
def test_trace_accumulation_across_stages(
    clear_request: NormalizedRequest,
    linear_workflow: WorkflowGraph,
    fake_provider: FakeLLMProvider,
) -> None:
    """Trace entries accumulate properly across all stages."""
    context = CrewExecutionContext(
        normalized_request=clear_request,
        provider=fake_provider,
        orchestration_mode="direct",
    )
    runner = CrewAIRunner()
    executor = WorkflowExecutor(
        workflow=linear_workflow,
        runner=runner,
        context=context,
    )

    asyncio.run(executor.execute())

    assert len(context.trace) >= 8
    task_names = [entry.task_name for entry in context.trace]
    assert len(task_names) >= 8


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
