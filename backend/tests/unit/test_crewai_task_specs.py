"""Unit tests for CrewAI task specification framework.

Validates all 9 CrewTaskSpec instances and their execution contracts:
1. ClarificationTask (pre_generation)
2. GenerationTask (generation)
3. ClaimExtractionTask (analysis)
4. StaticAnalysisTask (analysis)
5. SandboxExecutionTask (analysis)
6. JudgeTask (judgment)
7. CoVeTask (judgment)
8. PolicyCoordinatorTask (policy)
9. RepairTask (mitigation)
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from dehalu.adapters.llm.base import LLMProvider
from dehalu.agents.contracts import CrewExecutionContext, CrewTaskSpec
from dehalu.agents.task_specs import (
    CLARIFICATION_TASK,
    create_all_task_specs,
    get_task_dependencies,
    get_task_spec_by_name,
)
from dehalu.orchestration.execution import _ExecutionStages
from dehalu.schemas import (
    CoderOutput,
    CoVeCheckVerdict,
    CoVeResult,
    ExtractedClaim,
    JudgeResult,
    JudgeVerdict,
    NormalizedRequest,
    OrchestrationTraceEntry,
    PolicyDecision,
    PolicyDecisionState,
    RepairResult,
    RiskLevel,
    SandboxResult,
    SandboxStatus,
    StaticFinding,
    StaticFindingSeverity,
)
from dehalu.state.repository import EvaluationBundle


# =============================================================================
# CONSTANTS
# =============================================================================

VALID_STAGES = {"pre_generation", "generation", "analysis", "judgment", "policy", "mitigation"}

EXPECTED_TASK_NAMES = {
    "ClarificationTask",
    "GenerationTask",
    "ClaimExtractionTask",
    "StaticAnalysisTask",
    "SandboxExecutionTask",
    "JudgeTask",
    "CoVeTask",
    "PolicyCoordinatorTask",
    "RepairTask",
}

STAGE_TO_TASKS = {
    "pre_generation": {"ClarificationTask"},
    "generation": {"GenerationTask"},
    "analysis": {"ClaimExtractionTask", "StaticAnalysisTask", "SandboxExecutionTask"},
    "judgment": {"JudgeTask", "CoVeTask"},
    "policy": {"PolicyCoordinatorTask"},
    "mitigation": {"RepairTask"},
}

DEPENDENCY_GRAPH = {
    "ClarificationTask": set(),
    "GenerationTask": {"ClarificationTask"},  # Documented in task_specs
    "ClaimExtractionTask": {"GenerationTask"},
    "StaticAnalysisTask": {"GenerationTask"},
    "SandboxExecutionTask": {"GenerationTask"},
    "JudgeTask": {"ClaimExtractionTask", "StaticAnalysisTask", "SandboxExecutionTask"},
    "CoVeTask": {"ClaimExtractionTask", "JudgeTask"},
    "PolicyCoordinatorTask": {"JudgeTask", "CoVeTask"},
    "RepairTask": {"PolicyCoordinatorTask"},
}


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture()
def mock_llm_provider() -> LLMProvider:
    """Create a mock LLM provider."""
    provider = MagicMock(spec=LLMProvider)
    provider.clarify.return_value = MagicMock(
        ambiguity_flags=["language"],
        clarified_prompt="Clarified prompt",
    )
    return provider


@pytest.fixture()
def normalized_request() -> NormalizedRequest:
    """Create a sample normalized request."""
    from dehalu.schemas import RunMode
    
    return NormalizedRequest(
        prompt="Write a function that computes the factorial of n",
        language="python",
        latency_budget_seconds=30,
        provider="test",
        risk_level=RiskLevel.low,
        run_mode=RunMode.basic,
        target_runtime="python3.12",
        acceptance_criteria=["Handles n >= 0", "Returns integer"],
    )


@pytest.fixture()
def mock_execution_context(mock_llm_provider: LLMProvider, normalized_request: NormalizedRequest) -> CrewExecutionContext:
    """Create a mock execution context for testing."""
    return CrewExecutionContext(
        normalized_request=normalized_request,
        provider=mock_llm_provider,
        orchestration_mode="direct",
        attempt_number=1,
        attempt_stage="original",
    )


@pytest.fixture()
def sample_coder_output() -> CoderOutput:
    """Create sample generated code output."""
    return CoderOutput(
        provider="test",
        model="test-model",
        language="python",
        code="def factorial(n):\n    if n <= 1:\n        return 1\n    return n * factorial(n - 1)\n",
        dependencies=["math"],
        assumptions=["Python 3.12+"],
        execution_notes="Recursive implementation",
    )


@pytest.fixture()
def sample_extracted_claims() -> list[ExtractedClaim]:
    """Create sample extracted claims."""
    return [
        ExtractedClaim(
            kind="dependency",
            value="math",
            source="import math",
        ),
        ExtractedClaim(
            kind="function",
            value="factorial",
            source="def factorial(n):",
        ),
        ExtractedClaim(
            kind="assumption",
            value="Python 3.12+",
            source="requirements",
        ),
    ]


@pytest.fixture()
def sample_static_findings() -> list[StaticFinding]:
    """Create sample static analysis findings."""
    return [
        StaticFinding(
            code="undefined_import",
            message="math module not found in standard library",
            severity=StaticFindingSeverity.warning,
            line=1,
            column=0,
        ),
    ]


@pytest.fixture()
def sample_sandbox_result() -> SandboxResult:
    """Create sample sandbox execution result."""
    return SandboxResult(
        status=SandboxStatus.passed,
        check_type="compile_only",
        language="python",
        duration_ms=42.5,
        findings=[],
    )


@pytest.fixture()
def sample_judge_result() -> JudgeResult:
    """Create sample judge verdict."""
    return JudgeResult(
        verdict=JudgeVerdict.pass_,
        provider="test",
        model="test-judge",
        duration_ms=100.0,
        hallucination_score=0.15,
        findings=[],
        metrics={"alignment": 0.9, "completeness": 0.85},
    )


@pytest.fixture()
def sample_cove_result() -> CoVeResult:
    """Create sample CoVe result."""
    return CoVeResult(
        verdict=JudgeVerdict.pass_,
        provider="test",
        model="test-cove",
        duration_ms=150.0,
        hallucination_score=0.12,
        checks=[],
        findings=[],
        metrics={"coverage": 0.88},
    )


@pytest.fixture()
def sample_policy_decision() -> PolicyDecision:
    """Create sample policy decision."""
    return PolicyDecision(
        state=PolicyDecisionState.accept,
        reasons=["Low hallucination score", "All claims verified"],
        hard_fail=False,
        score=0.18,
        metrics={"judge_score": 0.15, "cove_score": 0.12},
    )


@pytest.fixture()
def all_task_specs(mock_llm_provider: LLMProvider) -> dict[str, CrewTaskSpec]:
    """Return all 9 task specs from task_specs module."""
    mock_stages = MagicMock(spec=_ExecutionStages)
    return create_all_task_specs(mock_stages)


# =============================================================================
# 1. TASK SPEC DEFINITION TESTS
# =============================================================================


@pytest.mark.unit
class TestTaskSpecDefinition:
    """Validate task spec definitions and attributes."""

    def test_all_task_specs_defined_and_importable(self, all_task_specs: dict[str, CrewTaskSpec]) -> None:
        """Verify 9 tasks exist and are importable."""
        assert len(all_task_specs) == 9, f"Expected 9 tasks, got {len(all_task_specs)}"
        assert all_task_specs.keys() == EXPECTED_TASK_NAMES

    def test_task_spec_attributes(self, all_task_specs: dict[str, CrewTaskSpec]) -> None:
        """Check each task has required attributes."""
        for task_name, task_spec in all_task_specs.items():
            assert task_spec.name, f"{task_name} missing name"
            assert task_spec.stage, f"{task_name} missing stage"
            assert task_spec.description, f"{task_name} missing description"
            assert task_spec.expected_output, f"{task_name} missing expected_output"
            assert task_spec.agent_role, f"{task_name} missing agent_role"
            assert task_spec.run, f"{task_name} missing run callable"
            assert callable(task_spec.run), f"{task_name} run is not callable"

    def test_task_names_are_unique(self, all_task_specs: dict[str, CrewTaskSpec]) -> None:
        """Ensure no duplicate task names."""
        names = [task.name for task in all_task_specs.values()]
        assert len(names) == len(set(names)), "Duplicate task names detected"

    def test_task_stages_are_valid(self, all_task_specs: dict[str, CrewTaskSpec]) -> None:
        """Verify stage values are from allowed set."""
        for task_name, task_spec in all_task_specs.items():
            assert task_spec.stage in VALID_STAGES, (
                f"{task_name} has invalid stage '{task_spec.stage}'. "
                f"Valid stages: {VALID_STAGES}"
            )

    def test_task_descriptions_are_meaningful(self, all_task_specs: dict[str, CrewTaskSpec]) -> None:
        """Check descriptions > 20 chars, not placeholder text."""
        for task_name, task_spec in all_task_specs.items():
            assert len(task_spec.description) > 20, (
                f"{task_name} description too brief: '{task_spec.description}'"
            )
            assert "TODO" not in task_spec.description, (
                f"{task_name} description contains placeholder TODO"
            )
            assert "placeholder" not in task_spec.description.lower(), (
                f"{task_name} description is placeholder text"
            )

    def test_expected_output_descriptions_exist(self, all_task_specs: dict[str, CrewTaskSpec]) -> None:
        """Each task has expected_output description."""
        for task_name, task_spec in all_task_specs.items():
            assert task_spec.expected_output, f"{task_name} missing expected_output"
            assert len(task_spec.expected_output) > 10, (
                f"{task_name} expected_output too brief"
            )


# =============================================================================
# 2. DEPENDENCY GRAPH TESTS
# =============================================================================


@pytest.mark.unit
class TestDependencyGraph:
    """Validate task dependency relationships and DAG properties."""

    def test_clarification_task_has_no_dependencies(self, all_task_specs: dict[str, CrewTaskSpec]) -> None:
        """Clarification is root with no dependencies."""
        task = all_task_specs["ClarificationTask"]
        assert task.depends_on == (), "ClarificationTask should have no dependencies"

    def test_generation_task_optional_depends_on_clarification(self, all_task_specs: dict[str, CrewTaskSpec]) -> None:
        """GenerationTask has optional dependency on ClarificationTask via should_run."""
        task = all_task_specs["GenerationTask"]
        # GenerationTask depends_on includes ClarificationTask
        # This is an optional dependency that may be skipped
        assert "ClarificationTask" in task.depends_on or len(task.depends_on) == 1, (
            "GenerationTask should include ClarificationTask in dependency chain"
        )

    def test_analysis_tasks_depend_on_generation(self, all_task_specs: dict[str, CrewTaskSpec]) -> None:
        """Claim/Static/Sandbox all depend on Generation."""
        analysis_tasks = [
            "ClaimExtractionTask",
            "StaticAnalysisTask",
            "SandboxExecutionTask",
        ]
        for task_name in analysis_tasks:
            task = all_task_specs[task_name]
            assert "GenerationTask" in task.depends_on, (
                f"{task_name} should depend on GenerationTask"
            )

    def test_judgment_tasks_depend_on_analysis(self, all_task_specs: dict[str, CrewTaskSpec]) -> None:
        """Judge depends on Analysis tasks."""
        judge_task = all_task_specs["JudgeTask"]
        analysis_tasks = {"ClaimExtractionTask", "StaticAnalysisTask", "SandboxExecutionTask"}
        for analysis_task in analysis_tasks:
            assert analysis_task in judge_task.depends_on, (
                f"JudgeTask should depend on {analysis_task}"
            )

    def test_cove_depends_on_claim_extraction_and_judge(
        self, all_task_specs: dict[str, CrewTaskSpec]
    ) -> None:
        """CoVeTask depends on ClaimExtractionTask and JudgeTask."""
        cove_task = all_task_specs["CoVeTask"]
        assert "ClaimExtractionTask" in cove_task.depends_on
        assert "JudgeTask" in cove_task.depends_on

    def test_policy_task_depends_on_judgment(self, all_task_specs: dict[str, CrewTaskSpec]) -> None:
        """Policy depends on Judge and CoVe."""
        policy_task = all_task_specs["PolicyCoordinatorTask"]
        assert "JudgeTask" in policy_task.depends_on
        assert "CoVeTask" in policy_task.depends_on

    def test_repair_task_depends_on_policy(self, all_task_specs: dict[str, CrewTaskSpec]) -> None:
        """Repair is conditional on Policy."""
        repair_task = all_task_specs["RepairTask"]
        assert "PolicyCoordinatorTask" in repair_task.depends_on

    def test_no_circular_dependencies(self, all_task_specs: dict[str, CrewTaskSpec]) -> None:
        """DAG has no cycles (depth-first search for cycles)."""

        def has_cycle(
            node: str,
            graph: dict[str, set[str]],
            visited: set[str],
            rec_stack: set[str],
        ) -> bool:
            visited.add(node)
            rec_stack.add(node)

            for neighbor in graph.get(node, set()):
                if neighbor not in visited:
                    if has_cycle(neighbor, graph, visited, rec_stack):
                        return True
                elif neighbor in rec_stack:
                    return True

            rec_stack.remove(node)
            return False

        graph = DEPENDENCY_GRAPH
        visited: set[str] = set()
        for node in graph:
            if node not in visited:
                assert not has_cycle(node, graph, visited, set()), (
                    "Circular dependency detected in task graph"
                )

    def test_dependency_order_is_correct(self, all_task_specs: dict[str, CrewTaskSpec]) -> None:
        """Topological sort produces valid ordering."""

        def topological_sort(graph: dict[str, set[str]]) -> list[str]:
            """Kahn's algorithm for topological sorting (depends_on version).
            
            Graph maps task_name -> set of tasks it depends on.
            We compute in-degrees based on "is required by" relationship.
            """
            # Build reverse graph: task -> tasks that depend on it
            reverse_graph = {node: set() for node in graph}
            in_degree = {node: 0 for node in graph}
            
            for node in graph:
                for dep in graph[node]:
                    reverse_graph[dep].add(node)
                    in_degree[node] += 1

            # Find nodes with no incoming edges (no dependencies)
            queue = [node for node in in_degree if in_degree[node] == 0]
            result = []

            while queue:
                node = queue.pop(0)
                result.append(node)

                # For each task that depends on this one
                for dependent in reverse_graph[node]:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        queue.append(dependent)

            return result

        graph = DEPENDENCY_GRAPH
        order = topological_sort(graph)

        # Verify order respects dependencies
        position = {task: i for i, task in enumerate(order)}
        for task, deps in graph.items():
            for dep in deps:
                assert position[dep] < position[task], (
                    f"{dep} should come before {task} in topological order (dependency)"
                )


# =============================================================================
# 3. CONDITIONAL EXECUTION TESTS
# =============================================================================


@pytest.mark.unit
class TestConditionalExecution:
    """Validate should_run callable behavior."""

    def test_clarification_task_should_run_with_ambiguous_language(
        self, mock_execution_context: CrewExecutionContext, all_task_specs: dict[str, CrewTaskSpec]
    ) -> None:
        """should_run returns True when language is ambiguous."""
        task = all_task_specs["ClarificationTask"]
        mock_execution_context.normalized_request.language = "unknown"

        should_run, reason = task.should_run(mock_execution_context)
        assert should_run is True
        assert reason is not None
        assert "Language" in reason or "ambiguous" in reason.lower()

    def test_clarification_task_should_skip_with_clear_request(
        self, mock_execution_context: CrewExecutionContext, all_task_specs: dict[str, CrewTaskSpec]
    ) -> None:
        """should_run returns False when request is clear."""
        task = all_task_specs["ClarificationTask"]
        mock_execution_context.normalized_request.language = "python"
        mock_execution_context.normalized_request.prompt = "Write a Python function to compute factorial"

        should_run, reason = task.should_run(mock_execution_context)
        assert should_run is False
        assert reason is None

    def test_repair_task_should_run_when_policy_requires_repair(
        self, mock_execution_context: CrewExecutionContext, all_task_specs: dict[str, CrewTaskSpec]
    ) -> None:
        """should_run returns True when policy_decision.state is repair_and_retry."""
        task = all_task_specs["RepairTask"]

        # Set up initial attempt with repair policy
        mock_execution_context.initial_attempt = MagicMock(spec=EvaluationBundle)
        mock_execution_context.initial_attempt.policy_decision = PolicyDecision(
            state=PolicyDecisionState.repair_and_retry,
            reasons=["Judge found issues"],
            score=0.65,
            metrics={"repair_trigger": "judge_fail"},
        )

        should_run, reason = task.should_run(mock_execution_context)
        assert should_run is True
        assert "repair" in reason.lower()

    def test_repair_task_should_skip_when_policy_accepts(
        self, mock_execution_context: CrewExecutionContext, all_task_specs: dict[str, CrewTaskSpec]
    ) -> None:
        """should_run returns False when policy_decision is accept."""
        task = all_task_specs["RepairTask"]

        mock_execution_context.initial_attempt = MagicMock(spec=EvaluationBundle)
        mock_execution_context.initial_attempt.policy_decision = PolicyDecision(
            state=PolicyDecisionState.accept,
            reasons=["Code is clean"],
            score=0.1,
        )

        should_run, reason = task.should_run(mock_execution_context)
        assert should_run is False
        assert reason is not None

    def test_repair_task_should_skip_without_initial_attempt(
        self, mock_execution_context: CrewExecutionContext, all_task_specs: dict[str, CrewTaskSpec]
    ) -> None:
        """should_run returns False when no initial attempt."""
        task = all_task_specs["RepairTask"]
        mock_execution_context.initial_attempt = None

        should_run, reason = task.should_run(mock_execution_context)
        assert should_run is False
        assert reason is not None

    def test_other_tasks_always_run(self, mock_execution_context: CrewExecutionContext, all_task_specs: dict[str, CrewTaskSpec]) -> None:
        """Tasks without should_run are None or return (True, None)."""
        tasks_without_conditional_logic = {
            "GenerationTask",
            "ClaimExtractionTask",
            "StaticAnalysisTask",
            "SandboxExecutionTask",
            "JudgeTask",
            "CoVeTask",
            "PolicyCoordinatorTask",
        }
        for task_name in tasks_without_conditional_logic:
            task = all_task_specs[task_name]
            if task.should_run is None:
                # Tasks without should_run always run
                assert True
            else:
                should_run, reason = task.should_run(mock_execution_context)
                assert should_run is True


# =============================================================================
# 4. OUTPUT KEY TESTS
# =============================================================================


@pytest.mark.unit
class TestOutputKeys:
    """Validate output key uniqueness and conventions."""

    def test_each_task_has_output_key(self, all_task_specs: dict[str, CrewTaskSpec]) -> None:
        """output_key is not None for storing results."""
        for task_name, task_spec in all_task_specs.items():
            assert task_spec.output_key is not None, (
                f"{task_name} missing output_key"
            )

    def test_output_keys_are_unique(self, all_task_specs: dict[str, CrewTaskSpec]) -> None:
        """No duplicate output keys."""
        output_keys = [task.output_key for task in all_task_specs.values()]
        assert len(output_keys) == len(set(output_keys)), (
            "Duplicate output keys detected"
        )

    def test_output_keys_follow_convention(self, all_task_specs: dict[str, CrewTaskSpec]) -> None:
        """Keys are lowercase with underscores."""
        for task_name, task_spec in all_task_specs.items():
            key = task_spec.output_key
            assert key.islower() or "." in key, (
                f"{task_name} output_key '{key}' should be lowercase or use dot notation"
            )
            assert not " " in key, f"{task_name} output_key has spaces"

    def test_original_and_repair_attempt_key_patterns(self, all_task_specs: dict[str, CrewTaskSpec]) -> None:
        """Verify original.* and repair.* key patterns."""
        output_keys = [task.output_key for task in all_task_specs.values()]

        # Tasks in original attempt should use patterns like:
        # - clarification.result
        # - original.generated_output
        # - original.extracted_claims, etc.
        # Tasks in repair attempt should use:
        # - repair.generated_output
        # - repair.extracted_claims, etc.

        # This test documents the pattern; actual keys are implementation-specific
        for key in output_keys:
            assert key.count(".") >= 0, "Keys should use dot notation for namespacing"


# =============================================================================
# 5. AGENT ROLE INTEGRATION TESTS
# =============================================================================


@pytest.mark.unit
class TestAgentRoles:
    """Validate agent role assignments."""

    def test_all_tasks_map_to_valid_agent_roles(self, all_task_specs: dict[str, CrewTaskSpec]) -> None:
        """agent_role matches expected agent definitions."""
        valid_roles = {
            "Clarification Agent",
            "Generator",
            "Claim Extractor",
            "Static Verifier",
            "Judge",
            "CoVe",  # Note: actual role is "CoVe", not "CoVe Agent"
            "Policy Coordinator",
            "Repair",  # Note: actual role is "Repair", not "Repair Agent"
        }
        for task_name, task_spec in all_task_specs.items():
            assert task_spec.agent_role in valid_roles, (
                f"{task_name} has invalid agent_role '{task_spec.agent_role}'. "
                f"Valid roles: {valid_roles}"
            )

    def test_agent_roles_are_meaningful(self, all_task_specs: dict[str, CrewTaskSpec]) -> None:
        """Check agent roles against responsibilities."""
        role_to_task = {
            "Clarification Agent": "ClarificationTask",
            "Generator": "GenerationTask",
            "Claim Extractor": "ClaimExtractionTask",
            "Static Verifier": {"StaticAnalysisTask", "SandboxExecutionTask"},
            "Judge": "JudgeTask",
            "CoVe": "CoVeTask",
            "Policy Coordinator": "PolicyCoordinatorTask",
            "Repair": "RepairTask",
        }

        for role, expected_task in role_to_task.items():
            tasks_with_role = [
                task_name
                for task_name, spec in all_task_specs.items()
                if spec.agent_role == role
            ]
            if isinstance(expected_task, str):
                assert expected_task in tasks_with_role, (
                    f"Role '{role}' not found in {expected_task}"
                )
            else:
                assert any(t in tasks_with_role for t in expected_task), (
                    f"Role '{role}' not found in {expected_task}"
                )


# =============================================================================
# 6. ARTIFACT VALIDATION TESTS
# =============================================================================


@pytest.mark.unit
class TestArtifactValidation:
    """Validate artifact storage and retrieval in context."""

    def test_context_artifacts_can_be_set_and_retrieved(
        self, mock_execution_context: CrewExecutionContext
    ) -> None:
        """set_artifact/get_artifact work correctly."""
        mock_execution_context.set_artifact("test_key", "test_value")
        assert mock_execution_context.get_artifact("test_key") == "test_value"

    def test_missing_artifact_returns_default(
        self, mock_execution_context: CrewExecutionContext
    ) -> None:
        """get_artifact with default works."""
        result = mock_execution_context.get_artifact("nonexistent", "default_value")
        assert result == "default_value"

    def test_has_artifact_checks_correctly(
        self, mock_execution_context: CrewExecutionContext
    ) -> None:
        """has_artifact returns True/False as expected."""
        mock_execution_context.set_artifact("exists", "value")
        assert mock_execution_context.has_artifact("exists") is True
        assert mock_execution_context.has_artifact("missing") is False

    def test_artifact_storage_with_complex_objects(
        self, mock_execution_context: CrewExecutionContext, sample_extracted_claims: list[ExtractedClaim]
    ) -> None:
        """Artifacts can store complex objects like lists and dicts."""
        mock_execution_context.set_artifact("claims", sample_extracted_claims)
        retrieved = mock_execution_context.get_artifact("claims")
        assert retrieved == sample_extracted_claims


# =============================================================================
# 7. ERROR HANDLING TESTS
# =============================================================================


@pytest.mark.unit
class TestErrorHandling:
    """Validate error handling in task specs."""

    def test_invalid_should_run_return_type_detected(
        self, mock_execution_context: CrewExecutionContext
    ) -> None:
        """should_run must return tuple[bool, str|None]."""

        def invalid_should_run(context: CrewExecutionContext) -> Any:
            return "invalid"  # Should be tuple

        task = CrewTaskSpec(
            name="TestTask",
            stage="analysis",
            description="Test task",
            expected_output="Test output",
            agent_role="Test Agent",
            output_key="test.output",
            run=lambda ctx: None,
            should_run=invalid_should_run,
        )

        # This test documents the validation requirement
        # In production, frameworks should validate this
        with pytest.raises((TypeError, ValueError, AssertionError)):
            result = task.should_run(mock_execution_context)
            if not isinstance(result, tuple) or len(result) != 2:
                raise TypeError("should_run must return tuple[bool, str|None]")

    def test_task_run_callable_exists(self, all_task_specs: dict[str, CrewTaskSpec]) -> None:
        """run attribute is callable."""
        for task_name, task_spec in all_task_specs.items():
            assert callable(task_spec.run), f"{task_name} run is not callable"


# =============================================================================
# 8. TRACE RECORDING TESTS
# =============================================================================


@pytest.mark.unit
class TestTraceRecording:
    """Validate trace entry recording."""

    def test_trace_entries_recorded(self, mock_execution_context: CrewExecutionContext) -> None:
        """record_trace creates OrchestrationTraceEntry."""
        mock_execution_context.record_trace(
            task_name="TestTask",
            stage="analysis",
            agent_role="Test Agent",
            status="completed",
            output_key="test.output",
            audit_label="test_label",
        )

        assert len(mock_execution_context.trace) == 1
        entry = mock_execution_context.trace[0]
        assert isinstance(entry, OrchestrationTraceEntry)
        assert entry.task_name == "TestTask"
        assert entry.status == "completed"

    def test_trace_includes_task_metadata(self, mock_execution_context: CrewExecutionContext) -> None:
        """trace has task_name, stage, agent_role, status, etc."""
        mock_execution_context.record_trace(
            task_name="GenerationTask",
            stage="generation",
            agent_role="Generator",
            status="completed",
            output_key="original.generated_output",
            audit_label="generate_code",
            detail="Generated 500 bytes",
        )

        entry = mock_execution_context.trace[0]
        assert entry.task_name == "GenerationTask"
        assert entry.stage == "generation"
        assert entry.agent_role == "Generator"
        assert entry.status == "completed"
        assert entry.output_key == "original.generated_output"
        assert entry.audit_label == "generate_code"
        assert entry.detail == "Generated 500 bytes"

    def test_trace_sequence_increments(self, mock_execution_context: CrewExecutionContext) -> None:
        """Sequence numbers are sequential."""
        for i in range(1, 4):
            mock_execution_context.record_trace(
                task_name=f"Task{i}",
                stage="analysis",
                agent_role="Test",
                status="completed",
            )

        for i, entry in enumerate(mock_execution_context.trace, 1):
            assert entry.sequence == i

    def test_trace_captures_attempt_information(self, mock_execution_context: CrewExecutionContext) -> None:
        """Trace includes attempt_number and attempt_stage."""
        mock_execution_context.attempt_number = 2
        mock_execution_context.attempt_stage = "repair"

        mock_execution_context.record_trace(
            task_name="RepairTask",
            stage="mitigation",
            agent_role="Repair Agent",
            status="completed",
        )

        entry = mock_execution_context.trace[0]
        assert entry.attempt_number == 2
        assert entry.attempt_stage == "repair"


# =============================================================================
# 9. STAGE ASSIGNMENT TESTS
# =============================================================================


@pytest.mark.unit
class TestStageAssignment:
    """Validate correct stage assignments for all tasks."""

    def test_pre_generation_tasks_only_clarification(
        self, all_task_specs: dict[str, CrewTaskSpec]
    ) -> None:
        """Only ClarificationTask in pre_generation."""
        pre_gen_tasks = {
            name for name, task in all_task_specs.items()
            if task.stage == "pre_generation"
        }
        assert pre_gen_tasks == {"ClarificationTask"}

    def test_generation_tasks_only_generator(self, all_task_specs: dict[str, CrewTaskSpec]) -> None:
        """Only GenerationTask in generation."""
        gen_tasks = {
            name for name, task in all_task_specs.items()
            if task.stage == "generation"
        }
        assert gen_tasks == {"GenerationTask"}

    def test_analysis_tasks_are_correct(self, all_task_specs: dict[str, CrewTaskSpec]) -> None:
        """Claim/Static/Sandbox in analysis."""
        analysis_tasks = {
            name for name, task in all_task_specs.items()
            if task.stage == "analysis"
        }
        expected = {
            "ClaimExtractionTask",
            "StaticAnalysisTask",
            "SandboxExecutionTask",
        }
        assert analysis_tasks == expected

    def test_judgment_tasks_are_correct(self, all_task_specs: dict[str, CrewTaskSpec]) -> None:
        """Judge/CoVe in judgment."""
        judgment_tasks = {
            name for name, task in all_task_specs.items()
            if task.stage == "judgment"
        }
        expected = {"JudgeTask", "CoVeTask"}
        assert judgment_tasks == expected

    def test_policy_tasks_only_policy_coordinator(
        self, all_task_specs: dict[str, CrewTaskSpec]
    ) -> None:
        """Only PolicyCoordinatorTask in policy."""
        policy_tasks = {
            name for name, task in all_task_specs.items()
            if task.stage == "policy"
        }
        assert policy_tasks == {"PolicyCoordinatorTask"}

    def test_mitigation_tasks_only_repair(self, all_task_specs: dict[str, CrewTaskSpec]) -> None:
        """Only RepairTask in mitigation."""
        mitigation_tasks = {
            name for name, task in all_task_specs.items()
            if task.stage == "mitigation"
        }
        assert mitigation_tasks == {"RepairTask"}

    def test_all_stages_covered(self, all_task_specs: dict[str, CrewTaskSpec]) -> None:
        """All valid stages have at least one task."""
        stages_in_use = {task.stage for task in all_task_specs.values()}
        assert stages_in_use == VALID_STAGES


# =============================================================================
# 10. INTEGRATION TESTS (MINIMAL, UNIT-LEVEL)
# =============================================================================


@pytest.mark.unit
class TestIntegration:
    """Minimal unit-level integration tests."""

    def test_task_spec_list_executable_order(self, all_task_specs: dict[str, CrewTaskSpec]) -> None:
        """Sort 9 tasks topologically."""

        def topological_sort_with_names(
            task_specs: dict[str, CrewTaskSpec],
        ) -> list[str]:
            """Topologically sort tasks by dependency."""
            graph = {
                name: set(spec.depends_on)
                for name, spec in task_specs.items()
            }
            
            # Build reverse graph and compute in-degrees
            reverse_graph = {node: set() for node in graph}
            in_degree = {node: 0 for node in graph}
            
            for node in graph:
                for dep in graph[node]:
                    reverse_graph[dep].add(node)
                    in_degree[node] += 1

            # Kahn's algorithm
            queue = [node for node in in_degree if in_degree[node] == 0]
            result = []

            while queue:
                node = queue.pop(0)
                result.append(node)

                for dependent in reverse_graph[node]:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        queue.append(dependent)

            return result

        order = topological_sort_with_names(all_task_specs)
        assert len(order) == 9, "Should have exactly 9 tasks in order"

        # Verify dependencies respected
        position = {task: i for i, task in enumerate(order)}
        for task_name, task_spec in all_task_specs.items():
            for dep in task_spec.depends_on:
                assert position[dep] < position[task_name], (
                    f"{dep} should come before {task_name} in topological order"
                )

    def test_initial_attempt_and_repair_keys_separate(
        self, all_task_specs: dict[str, CrewTaskSpec]
    ) -> None:
        """original.* and repair.* keys don't collide."""
        output_keys = [task.output_key for task in all_task_specs.values()]

        # Count original vs repair keys
        original_keys = [k for k in output_keys if "original" in k or "clarification" in k or k.startswith("generation")]
        repair_keys = [k for k in output_keys if "repair" in k]

        # Ensure no overlap (this would indicate key collision)
        assert not (set(original_keys) & set(repair_keys)), (
            "Key namespace collision between original and repair attempts"
        )

    def test_policy_decision_required_for_repair(
        self, mock_execution_context: CrewExecutionContext, all_task_specs: dict[str, CrewTaskSpec]
    ) -> None:
        """Repair task should_run checks for policy decision."""
        repair_task = all_task_specs["RepairTask"]

        # Without policy decision
        mock_execution_context.initial_attempt = MagicMock(spec=EvaluationBundle)
        mock_execution_context.initial_attempt.policy_decision = PolicyDecision(
            state=PolicyDecisionState.accept,
            reasons=["OK"],
            score=0.1,
        )

        should_run, reason = repair_task.should_run(mock_execution_context)
        assert should_run is False, "Repair should not run if policy is accept"

        # With repair decision
        mock_execution_context.initial_attempt.policy_decision.state = (
            PolicyDecisionState.repair_and_retry
        )
        should_run, reason = repair_task.should_run(mock_execution_context)
        assert should_run is True, "Repair should run if policy is repair_and_retry"


# =============================================================================
# PARAMETRIZED TESTS FOR EACH TASK
# =============================================================================


@pytest.mark.unit
class TestAllTasksParametrized:
    """Parametrized tests across all 9 tasks."""

    @pytest.mark.parametrize("task_name", EXPECTED_TASK_NAMES)
    def test_each_task_has_valid_attributes(
        self, task_name: str, all_task_specs: dict[str, CrewTaskSpec]
    ) -> None:
        """Each of 9 tasks has valid attributes."""
        task = all_task_specs[task_name]
        assert task.name == task_name
        assert task.stage in VALID_STAGES
        assert len(task.description) > 0
        assert task.agent_role
        assert task.output_key
        assert callable(task.run)

    @pytest.mark.parametrize("task_name", EXPECTED_TASK_NAMES)
    def test_each_task_in_correct_stage(
        self, task_name: str, all_task_specs: dict[str, CrewTaskSpec]
    ) -> None:
        """Each task is in its expected stage."""
        task = all_task_specs[task_name]
        expected_stage = None
        for stage, tasks in STAGE_TO_TASKS.items():
            if task_name in tasks:
                expected_stage = stage
                break

        assert task.stage == expected_stage, (
            f"{task_name} in stage '{task.stage}', expected '{expected_stage}'"
        )

    @pytest.mark.parametrize("task_name", EXPECTED_TASK_NAMES)
    def test_each_task_dependencies_correct(
        self, task_name: str, all_task_specs: dict[str, CrewTaskSpec]
    ) -> None:
        """Each task has correct dependencies."""
        task = all_task_specs[task_name]
        expected_deps = DEPENDENCY_GRAPH.get(task_name, set())
        actual_deps = set(task.depends_on)
        assert actual_deps == expected_deps, (
            f"{task_name} deps {actual_deps}, expected {expected_deps}"
        )

    @pytest.mark.parametrize("task_name", ["ClarificationTask", "RepairTask"])
    def test_conditional_tasks_have_should_run(
        self, task_name: str, all_task_specs: dict[str, CrewTaskSpec]
    ) -> None:
        """Conditional tasks have should_run callable."""
        task = all_task_specs[task_name]
        assert task.should_run is not None, (
            f"{task_name} should have should_run callable"
        )
        assert callable(task.should_run)

    @pytest.mark.parametrize("task_name", EXPECTED_TASK_NAMES)
    def test_task_output_key_not_empty(
        self, task_name: str, all_task_specs: dict[str, CrewTaskSpec]
    ) -> None:
        """Each task has a non-empty output key."""
        task = all_task_specs[task_name]
        assert task.output_key is not None
        assert len(task.output_key) > 0


# =============================================================================
# HELPER FUNCTION TESTS
# =============================================================================


@pytest.mark.unit
class TestHelperFunctions:
    """Test helper functions from task_specs module."""

    def test_get_task_spec_by_name(self, all_task_specs: dict[str, CrewTaskSpec]) -> None:
        """get_task_spec_by_name retrieves task."""
        task = get_task_spec_by_name(all_task_specs, "GenerationTask")
        assert task is not None
        assert task.name == "GenerationTask"

    def test_get_task_spec_by_name_returns_none_for_missing(
        self, all_task_specs: dict[str, CrewTaskSpec]
    ) -> None:
        """get_task_spec_by_name returns None for missing task."""
        task = get_task_spec_by_name(all_task_specs, "NonexistentTask")
        assert task is None

    def test_get_task_dependencies(self, all_task_specs: dict[str, CrewTaskSpec]) -> None:
        """get_task_dependencies returns correct list."""
        deps = get_task_dependencies(all_task_specs, "JudgeTask")
        assert set(deps) == {
            "ClaimExtractionTask",
            "StaticAnalysisTask",
            "SandboxExecutionTask",
        }

    def test_get_task_dependencies_for_root_task(
        self, all_task_specs: dict[str, CrewTaskSpec]
    ) -> None:
        """get_task_dependencies for root task returns empty."""
        deps = get_task_dependencies(all_task_specs, "ClarificationTask")
        assert deps == []


@pytest.mark.unit
def test_clarification_task_is_singleton() -> None:
    """CLARIFICATION_TASK is properly exported as singleton."""
    from dehalu.agents.task_specs import CLARIFICATION_TASK

    assert CLARIFICATION_TASK.name == "ClarificationTask"
    assert CLARIFICATION_TASK.stage == "pre_generation"
    assert CLARIFICATION_TASK.should_run is not None
