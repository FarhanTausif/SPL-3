from __future__ import annotations

from dataclasses import dataclass

from dehalu.agents.compat import Agent, HAS_CREWAI, Task
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


ROLE_DEFINITIONS = {
    CLARIFICATION_AGENT["role"]: CLARIFICATION_AGENT,
    GENERATOR_AGENT["role"]: GENERATOR_AGENT,
    CLAIM_EXTRACTOR_AGENT["role"]: CLAIM_EXTRACTOR_AGENT,
    STATIC_VERIFIER_AGENT["role"]: STATIC_VERIFIER_AGENT,
    JUDGE_AGENT["role"]: JUDGE_AGENT,
    COVE_AGENT["role"]: COVE_AGENT,
    REPAIR_AGENT["role"]: REPAIR_AGENT,
    POLICY_COORDINATOR_AGENT["role"]: POLICY_COORDINATOR_AGENT,
}


@dataclass(slots=True)
class _CrewPlan:
    agents: list[Agent]
    tasks: list[Task]


class CrewAIRunner:
    def __init__(self, verbose: bool = False) -> None:
        self.verbose = verbose

    @property
    def available(self) -> bool:
        return HAS_CREWAI

    def run(
        self,
        context: CrewExecutionContext,
        task_specs: list[CrewTaskSpec],
    ) -> CrewExecutionContext:
        crew = self._build_crew(task_specs)
        context.notes.append(
            f"Built crew with {len(crew.agents)} agents and {len(crew.tasks)} tasks."
        )
        context.record_trace(
            task_name="crew_bootstrap",
            stage="orchestration",
            agent_role="Crew Runtime",
            status="ready",
            detail="native_crewai" if self.available else "compat_fallback",
        )

        for task_spec in task_specs:
            if task_spec.should_run is not None:
                should_run, reason = task_spec.should_run(context)
                if not should_run:
                    context.record_trace(
                        task_name=task_spec.name,
                        stage=task_spec.stage,
                        agent_role=task_spec.agent_role,
                        status="skipped",
                        output_key=task_spec.output_key,
                        audit_label=task_spec.audit_label,
                        detail=reason,
                    )
                    continue

            missing_dependencies = [
                dependency for dependency in task_spec.depends_on if not context.has_artifact(dependency)
            ]
            if missing_dependencies:
                raise ValueError(
                    f"Task '{task_spec.name}' is missing dependencies: {', '.join(missing_dependencies)}"
                )

            context.record_trace(
                task_name=task_spec.name,
                stage=task_spec.stage,
                agent_role=task_spec.agent_role,
                status="started",
                output_key=task_spec.output_key,
                audit_label=task_spec.audit_label,
            )
            task_spec.run(context)
            context.record_trace(
                task_name=task_spec.name,
                stage=task_spec.stage,
                agent_role=task_spec.agent_role,
                status="completed",
                output_key=task_spec.output_key,
                audit_label=task_spec.audit_label,
            )
        return context

    def _build_crew(self, task_specs: list[CrewTaskSpec]) -> _CrewPlan:
        agents_by_role = {
            role: Agent(verbose=self.verbose, allow_delegation=False, **definition)
            for role, definition in ROLE_DEFINITIONS.items()
            if any(task_spec.agent_role == role for task_spec in task_specs)
        }
        tasks = [
            Task(
                description=task_spec.description,
                expected_output=task_spec.expected_output,
                agent=agents_by_role[task_spec.agent_role],
            )
            for task_spec in task_specs
        ]
        agents = list({task.agent.role: task.agent for task in tasks}.values())
        return _CrewPlan(agents=agents, tasks=tasks)
