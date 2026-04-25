from __future__ import annotations

from dehalu.agents.compat import Agent, Crew, Process, Task
from dehalu.agents.contracts import CrewExecutionContext, CrewTaskDefinition
from dehalu.agents.roles import CODER_AGENT, REPAIR_AGENT, VERIFIER_AGENT


class CrewAIRunner:
    def __init__(self, verbose: bool = False) -> None:
        self.verbose = verbose

    def run(
        self,
        context: CrewExecutionContext,
        task_definitions: list[CrewTaskDefinition],
    ) -> CrewExecutionContext:
        crew = self._build_crew(task_definitions)
        context.notes.append(
            f"Built crew with {len(crew.agents)} agents and {len(crew.tasks)} tasks."
        )
        for task_definition in task_definitions:
            task_definition.run(context)
            context.notes.append(f"Completed crew task: {task_definition.name}.")
        return context

    def _build_crew(self, task_definitions: list[CrewTaskDefinition]) -> Crew:
        agents_by_role = {
            CODER_AGENT["role"]: Agent(verbose=self.verbose, allow_delegation=False, **CODER_AGENT),
            VERIFIER_AGENT["role"]: Agent(verbose=self.verbose, allow_delegation=False, **VERIFIER_AGENT),
            REPAIR_AGENT["role"]: Agent(verbose=self.verbose, allow_delegation=False, **REPAIR_AGENT),
        }
        tasks = [
            Task(
                description=definition.description,
                expected_output=definition.expected_output,
                agent=agents_by_role[definition.agent_role],
            )
            for definition in task_definitions
        ]
        agents = list({task.agent.role: task.agent for task in tasks}.values())
        return Crew(
            agents=agents,
            tasks=tasks,
            process=Process.sequential,
            verbose=self.verbose,
        )
