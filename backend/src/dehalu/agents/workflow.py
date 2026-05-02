"""Workflow Orchestration Engine for CrewAI Agent Coordination.

This module implements DAG-based task sequencing, parallelism, conditional branching,
and repair loop management for the DeHalu multi-agent verification pipeline.

Key components:
- WorkflowNode: Represents a single task in the workflow DAG
- WorkflowGraph: DAG representing the complete workflow with validation
- WorkflowExecutor: Orchestrates task execution following the DAG
- Factory functions: Build different workflow types (linear, repair-aware, etc.)

The module supports:
- Linear workflow: Generation → Verification → Policy
- Repair workflow: Linear + conditional Repair → Re-verify → Policy
- Parallelization: Claims, Static, Sandbox run in parallel; Judge and CoVe in parallel
- Conditional execution: Clarification (optional), Repair (conditional on policy)
- Bounded repair: N=1 (one retry maximum)
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Callable

from dehalu.agents.contracts import CrewExecutionContext, CrewTaskSpec
from dehalu.agents.runner import CrewAIRunner
from dehalu.schemas import PolicyDecisionState


class WorkflowValidationError(Exception):
    """Raised when workflow DAG is invalid."""

    pass


class MissingDependencyError(Exception):
    """Raised when task dependencies are not satisfied."""

    pass


class WorkflowExecutionError(Exception):
    """Raised when workflow execution fails."""

    pass


@dataclass(slots=True)
class WorkflowNode:
    """Represents a single task in the workflow DAG.

    Attributes:
        task_spec: CrewTaskSpec instance for this task
        depends_on: List of task names this task depends on
        parallel_with: List of task names that can run in parallel with this task
        condition: Optional callable that determines if task should run
    """

    task_spec: CrewTaskSpec
    depends_on: list[str] = field(default_factory=list)
    parallel_with: list[str] = field(default_factory=list)
    condition: Callable[[CrewExecutionContext], bool] | None = None

    @property
    def name(self) -> str:
        """Task name from spec."""
        return self.task_spec.name


@dataclass(slots=True)
class WorkflowGraph:
    """DAG representing the complete workflow.

    Attributes:
        nodes: Mapping of task name to WorkflowNode
        entry_points: Initial tasks (no dependencies)
        exit_point: Final task name
        repair_entry: Task name where repair loop re-enters (usually GenerationTask)
    """

    nodes: dict[str, WorkflowNode] = field(default_factory=dict)
    entry_points: list[str] = field(default_factory=list)
    exit_point: str = ""
    repair_entry: str = ""

    def topological_sort(self) -> list[str]:
        """Return tasks in topological execution order.

        Uses Kahn's algorithm to sort tasks by dependencies.

        Returns:
            List of task names in execution order

        Raises:
            WorkflowValidationError: If cycle detected
        """
        # Build in-degree map
        in_degree = {name: 0 for name in self.nodes}
        for node in self.nodes.values():
            for dep in node.depends_on:
                if dep in in_degree:
                    in_degree[node.name] += 1

        # Find all nodes with no incoming edges
        queue = [name for name, degree in in_degree.items() if degree == 0]
        result = []

        while queue:
            node_name = queue.pop(0)
            result.append(node_name)

            # Reduce in-degree for all dependent tasks
            for other_name, other_node in self.nodes.items():
                if node_name in other_node.depends_on:
                    in_degree[other_name] -= 1
                    if in_degree[other_name] == 0:
                        queue.append(other_name)

        if len(result) != len(self.nodes):
            raise WorkflowValidationError("Cycle detected in workflow DAG")

        return result

    def get_parallelizable_tasks(self, completed_tasks: set[str]) -> list[str]:
        """Find tasks ready to run in parallel.

        A task is ready if all its dependencies are completed.

        Args:
            completed_tasks: Set of already-completed task names

        Returns:
            List of task names that can run next
        """
        ready = []
        for name, node in self.nodes.items():
            if name not in completed_tasks:
                # Check if all dependencies are completed
                if all(dep in completed_tasks for dep in node.depends_on):
                    ready.append(name)
        return ready

    def validate(self) -> tuple[bool, list[str]]:
        """Validate workflow structure.

        Checks for:
        - Cycles in DAG
        - Missing dependencies
        - Entry points have no dependencies
        - Exit point exists
        - Repair entry exists if repair workflow

        Returns:
            Tuple of (is_valid: bool, error_messages: list[str])
        """
        errors = []

        # Check for cycles
        try:
            self.topological_sort()
        except WorkflowValidationError as e:
            errors.append(str(e))

        # Check entry points have no dependencies
        for entry in self.entry_points:
            if entry not in self.nodes:
                errors.append(f"Entry point '{entry}' not in nodes")
            elif self.nodes[entry].depends_on:
                errors.append(f"Entry point '{entry}' has dependencies")

        # Check exit point exists
        if not self.exit_point:
            errors.append("Exit point not specified")
        elif self.exit_point not in self.nodes:
            errors.append(f"Exit point '{self.exit_point}' not in nodes")

        # Check all dependencies exist
        for name, node in self.nodes.items():
            for dep in node.depends_on:
                if dep not in self.nodes:
                    errors.append(f"Task '{name}' depends on missing task '{dep}'")

        # Check repair entry if present
        if self.repair_entry and self.repair_entry not in self.nodes:
            errors.append(f"Repair entry '{self.repair_entry}' not in nodes")

        return len(errors) == 0, errors


@dataclass(slots=True)
class WorkflowExecutor:
    """Orchestrates task execution following workflow DAG.

    Executes tasks in topological order, handling parallelization,
    conditional execution, and repair branching.

    Attributes:
        workflow: WorkflowGraph to execute
        runner: CrewAIRunner instance
        context: CrewExecutionContext for artifact storage
    """

    workflow: WorkflowGraph
    runner: CrewAIRunner
    context: CrewExecutionContext
    completed_tasks: set[str] = field(default_factory=set)
    task_results: dict[str, Any] = field(default_factory=dict)

    async def execute(self) -> None:
        """Run workflow end-to-end.

        Executes all tasks in topological order, handling parallelization,
        conditional execution, and repair branching.

        Raises:
            WorkflowValidationError: If workflow is invalid
            MissingDependencyError: If task dependencies are not satisfied
            WorkflowExecutionError: If task execution fails
        """
        # Validate workflow
        valid, errors = self.workflow.validate()
        if not valid:
            raise WorkflowValidationError(f"Invalid workflow: {errors}")

        # Execute workflow
        while not self._is_complete():
            # Get next batch of ready tasks
            ready_tasks = self.workflow.get_parallelizable_tasks(self.completed_tasks)

            if not ready_tasks:
                # No tasks ready but not complete - should be caught by validation
                raise WorkflowExecutionError("No tasks ready but workflow not complete")

            # Filter by condition (clarification, repair)
            tasks_to_run = [t for t in ready_tasks if self._should_run_task(t)]

            if tasks_to_run:
                # Execute tasks (can be parallelized)
                for task_name in tasks_to_run:
                    self._execute_task(task_name)

                # Mark as completed
                self.completed_tasks.update(tasks_to_run)

            # Check for policy decision and repair branching
            if "PolicyCoordinatorTask" in self.completed_tasks and "RepairTask" not in self.completed_tasks:
                if (
                    self.context.policy_decision
                    and self.context.policy_decision.state == PolicyDecisionState.repair_and_retry
                ):
                    # Execute repair branch
                    await self._execute_repair_branch()

    def _execute_task(self, task_name: str) -> None:
        """Execute single task and record results.

        Args:
            task_name: Name of task to execute

        Raises:
            MissingDependencyError: If dependencies not satisfied
        """
        node = self.workflow.nodes[task_name]
        task_spec = node.task_spec

        # Validate dependencies
        missing = [dep for dep in task_spec.depends_on if dep not in self.completed_tasks]
        if missing:
            raise MissingDependencyError(f"Task {task_name} missing: {missing}")

        # Check condition
        if not self._should_run_task(task_name):
            return

        # Execute task via runner
        self.runner.run(self.context, [task_spec])
        self.task_results[task_name] = True

    def _should_run_task(self, task_name: str) -> bool:
        """Check if task should run based on conditions.

        Args:
            task_name: Name of task to check

        Returns:
            True if task should run, False otherwise
        """
        node = self.workflow.nodes[task_name]
        task_spec = node.task_spec

        # Check task's should_run condition
        if task_spec.should_run is not None:
            should_run, _ = task_spec.should_run(self.context)
            if not should_run:
                return False

        # Check workflow node condition
        if node.condition is not None:
            return node.condition(self.context)

        return True

    async def _execute_repair_branch(self) -> None:
        """Execute repair branch (repair + re-verify).

        Executes:
        1. RepairTask
        2. ClaimExtractionTask, StaticAnalysisTask, SandboxExecutionTask (re-verify, parallel)
        3. JudgeTask, CoVeTask (parallel)
        4. PolicyCoordinatorTask (final decision)
        """
        # Mark attempt as repair
        if self.context.generated_output:
            self.context.reset_attempt_state(
                attempt_number=2,
                attempt_stage="repair",
                generated_output=self.context.generated_output,
            )

        # Execute repair
        repair_node = self.workflow.nodes.get("RepairTask")
        if repair_node:
            self._execute_task("RepairTask")
            self.completed_tasks.add("RepairTask")

        # Re-verify (same as initial but with allow_repair=false)
        re_verify_tasks = [
            "ClaimExtractionTask",
            "StaticAnalysisTask",
            "SandboxExecutionTask",
            "JudgeTask",
            "CoVeTask",
        ]
        for task_name in re_verify_tasks:
            if task_name in self.workflow.nodes:
                self._execute_task(task_name)
                self.completed_tasks.add(task_name)

        # Final policy decision
        if "PolicyCoordinatorTask" in self.workflow.nodes:
            self._execute_task("PolicyCoordinatorTask")
            self.completed_tasks.add("PolicyCoordinatorTask")

    def _is_complete(self) -> bool:
        """Check if workflow is done.

        Returns:
            True if exit point is completed, False otherwise
        """
        return self.workflow.exit_point in self.completed_tasks


# =============================================================================
# WORKFLOW FACTORY FUNCTIONS
# =============================================================================


def build_linear_workflow(task_specs: dict[str, CrewTaskSpec]) -> WorkflowGraph:
    """Build linear workflow without repair.

    Flow:
    - ClarificationTask (optional, conditional)
    - GenerationTask (depends on Clarification)
    - ClaimExtractionTask, StaticAnalysisTask, SandboxExecutionTask (parallel)
    - JudgeTask, CoVeTask (parallel)
    - PolicyCoordinatorTask (final)

    Args:
        task_specs: Dictionary of task_name -> CrewTaskSpec

    Returns:
        WorkflowGraph with linear execution flow
    """
    graph = WorkflowGraph()

    # Task 1: Clarification (optional, entry point)
    if "ClarificationTask" in task_specs:
        clarification_spec = task_specs["ClarificationTask"]
        graph.nodes["ClarificationTask"] = WorkflowNode(
            task_spec=clarification_spec,
            depends_on=[],
            parallel_with=[],
            condition=None,
        )

    # Task 2: Generation (depends on Clarification, but Clarification is optional)
    if "GenerationTask" in task_specs:
        generation_spec = task_specs["GenerationTask"]
        graph.nodes["GenerationTask"] = WorkflowNode(
            task_spec=generation_spec,
            depends_on=["ClarificationTask"] if "ClarificationTask" in task_specs else [],
            parallel_with=[],
            condition=None,
        )

    # Task 3: Claim Extraction (parallel with Static and Sandbox)
    if "ClaimExtractionTask" in task_specs:
        claim_spec = task_specs["ClaimExtractionTask"]
        graph.nodes["ClaimExtractionTask"] = WorkflowNode(
            task_spec=claim_spec,
            depends_on=["GenerationTask"],
            parallel_with=["StaticAnalysisTask", "SandboxExecutionTask"],
            condition=None,
        )

    # Task 4: Static Analysis (parallel with Claims and Sandbox)
    if "StaticAnalysisTask" in task_specs:
        static_spec = task_specs["StaticAnalysisTask"]
        graph.nodes["StaticAnalysisTask"] = WorkflowNode(
            task_spec=static_spec,
            depends_on=["GenerationTask"],
            parallel_with=["ClaimExtractionTask", "SandboxExecutionTask"],
            condition=None,
        )

    # Task 5: Sandbox Execution (parallel with Claims and Static)
    if "SandboxExecutionTask" in task_specs:
        sandbox_spec = task_specs["SandboxExecutionTask"]
        graph.nodes["SandboxExecutionTask"] = WorkflowNode(
            task_spec=sandbox_spec,
            depends_on=["GenerationTask"],
            parallel_with=["ClaimExtractionTask", "StaticAnalysisTask"],
            condition=None,
        )

    # Task 6: Judge (depends on Claims, Static, Sandbox)
    if "JudgeTask" in task_specs:
        judge_spec = task_specs["JudgeTask"]
        graph.nodes["JudgeTask"] = WorkflowNode(
            task_spec=judge_spec,
            depends_on=["ClaimExtractionTask", "StaticAnalysisTask", "SandboxExecutionTask"],
            parallel_with=["CoVeTask"],
            condition=None,
        )

    # Task 7: CoVe (parallel with Judge)
    if "CoVeTask" in task_specs:
        cove_spec = task_specs["CoVeTask"]
        graph.nodes["CoVeTask"] = WorkflowNode(
            task_spec=cove_spec,
            depends_on=["ClaimExtractionTask", "JudgeTask"],
            parallel_with=["JudgeTask"],
            condition=None,
        )

    # Task 8: Policy Coordinator (depends on Judge, CoVe) - EXIT POINT
    if "PolicyCoordinatorTask" in task_specs:
        policy_spec = task_specs["PolicyCoordinatorTask"]
        graph.nodes["PolicyCoordinatorTask"] = WorkflowNode(
            task_spec=policy_spec,
            depends_on=["JudgeTask", "CoVeTask"],
            parallel_with=[],
            condition=None,
        )

    # Set entry points and exit point
    graph.entry_points = (
        ["ClarificationTask"] if "ClarificationTask" in task_specs else ["GenerationTask"]
    )
    graph.exit_point = "PolicyCoordinatorTask"
    graph.repair_entry = "GenerationTask"

    return graph


def build_repair_aware_workflow(task_specs: dict[str, CrewTaskSpec]) -> WorkflowGraph:
    """Build repair-aware workflow with bounded repair loop.

    Flow:
    - Linear workflow up to PolicyCoordinatorTask
    - If policy decision is "repair_and_retry":
      - RepairTask
      - Re-verify (Claims, Static, Sandbox, Judge, CoVe)
      - Final PolicyCoordinatorTask
    - No further retries (bounded to N=1)

    Args:
        task_specs: Dictionary of task_name -> CrewTaskSpec

    Returns:
        WorkflowGraph with repair branching support
    """
    # Start with linear workflow
    graph = build_linear_workflow(task_specs)

    # Add Repair task and make it conditionally executable
    if "RepairTask" in task_specs:
        repair_spec = task_specs["RepairTask"]

        def repair_should_run(context: CrewExecutionContext) -> bool:
            """Repair only if policy decision requires it."""
            return (
                context.policy_decision is not None
                and context.policy_decision.state == PolicyDecisionState.repair_and_retry
            )

        graph.nodes["RepairTask"] = WorkflowNode(
            task_spec=repair_spec,
            depends_on=["PolicyCoordinatorTask"],
            parallel_with=[],
            condition=repair_should_run,
        )

    return graph


def build_direct_execution_workflow(task_specs: dict[str, CrewTaskSpec]) -> WorkflowGraph:
    """Build workflow for DirectExecutionEngine mode.

    Alias for build_linear_workflow().
    Used in direct/synchronous execution mode.

    Args:
        task_specs: Dictionary of task_name -> CrewTaskSpec

    Returns:
        WorkflowGraph with linear execution flow
    """
    return build_linear_workflow(task_specs)


def build_advanced_execution_workflow(task_specs: dict[str, CrewTaskSpec]) -> WorkflowGraph:
    """Build workflow for AdvancedExecutionEngine mode (worker-backed).

    Alias for build_repair_aware_workflow().
    Used in advanced/asynchronous worker-backed mode.

    Args:
        task_specs: Dictionary of task_name -> CrewTaskSpec

    Returns:
        WorkflowGraph with repair branching support
    """
    return build_repair_aware_workflow(task_specs)


# =============================================================================
# WORKFLOW UTILITIES
# =============================================================================


def get_workflow_summary(workflow: WorkflowGraph) -> str:
    """Get human-readable summary of workflow structure.

    Args:
        workflow: WorkflowGraph to summarize

    Returns:
        Multi-line string with workflow information
    """
    lines = [
        "Workflow Summary",
        "=" * 60,
        f"Total tasks: {len(workflow.nodes)}",
        f"Entry points: {', '.join(workflow.entry_points)}",
        f"Exit point: {workflow.exit_point}",
        f"Repair entry: {workflow.repair_entry}",
        "",
        "Tasks by Stage:",
    ]

    # Group tasks by stage
    stages: dict[str, list[str]] = {}
    for name, node in workflow.nodes.items():
        stage = node.task_spec.stage
        if stage not in stages:
            stages[stage] = []
        stages[stage].append(name)

    for stage in sorted(stages.keys()):
        lines.append(f"  {stage}:")
        for task in stages[stage]:
            node = workflow.nodes[task]
            deps = ", ".join(node.depends_on) if node.depends_on else "none"
            lines.append(f"    - {task} (depends on: {deps})")

    return "\n".join(lines)


def estimate_workflow_duration(
    workflow: WorkflowGraph, avg_task_duration_ms: int = 500
) -> int:
    """Estimate total workflow execution time accounting for parallelism.

    Calculates critical path through DAG, accounting for tasks that
    can run in parallel.

    Args:
        workflow: WorkflowGraph to analyze
        avg_task_duration_ms: Average task duration in milliseconds

    Returns:
        Estimated total duration in milliseconds
    """
    if not workflow.nodes:
        return 0

    # Build task depth map (longest path to each task)
    task_depth: dict[str, int] = {}

    # Topological sort to process in order
    sorted_tasks = workflow.topological_sort()

    for task_name in sorted_tasks:
        node = workflow.nodes[task_name]
        if not node.depends_on:
            task_depth[task_name] = avg_task_duration_ms
        else:
            # Depth is max depth of dependencies + this task's duration
            max_dep_depth = max(
                (task_depth.get(dep, avg_task_duration_ms) for dep in node.depends_on),
                default=0,
            )
            task_depth[task_name] = max_dep_depth + avg_task_duration_ms

    # Total duration is depth of exit point
    return task_depth.get(workflow.exit_point, avg_task_duration_ms)


def visualize_workflow(workflow: WorkflowGraph) -> str:
    """Generate ASCII art DAG visualization for debugging.

    Args:
        workflow: WorkflowGraph to visualize

    Returns:
        ASCII art string representing the workflow DAG
    """
    if not workflow.nodes:
        return "Empty workflow"

    lines = ["Workflow DAG Visualization", "=" * 60]

    # Topological sort for visualization
    sorted_tasks = workflow.topological_sort()

    # Build level map (which row each task appears in)
    task_level: dict[str, int] = {}
    for i, task in enumerate(sorted_tasks):
        task_level[task] = i

    # Group tasks by level for better visualization
    levels: dict[int, list[str]] = {}
    for task, level in task_level.items():
        if level not in levels:
            levels[level] = []
        levels[level].append(task)

    # Render by levels
    for level in sorted(levels.keys()):
        tasks = levels[level]
        if len(tasks) == 1:
            # Single task
            task = tasks[0]
            node = workflow.nodes[task]
            if node.depends_on:
                lines.append(f"{task}")
                lines.append(f"  ↑ deps: {', '.join(node.depends_on)}")
            else:
                lines.append(f"{task} [ENTRY]")
        else:
            # Multiple tasks (parallel)
            lines.append(f"[Parallel Level {level}]")
            for task in sorted(tasks):
                node = workflow.nodes[task]
                deps = f" (deps: {', '.join(node.depends_on)})" if node.depends_on else ""
                lines.append(f"  - {task}{deps}")

        if level < max(levels.keys()):
            lines.append("    ↓")

    # Mark exit point
    lines.append("")
    lines.append(f"[EXIT: {workflow.exit_point}]")

    return "\n".join(lines)


__all__ = [
    "WorkflowNode",
    "WorkflowGraph",
    "WorkflowExecutor",
    "WorkflowValidationError",
    "MissingDependencyError",
    "WorkflowExecutionError",
    "build_linear_workflow",
    "build_repair_aware_workflow",
    "build_direct_execution_workflow",
    "build_advanced_execution_workflow",
    "get_workflow_summary",
    "estimate_workflow_duration",
    "visualize_workflow",
]
