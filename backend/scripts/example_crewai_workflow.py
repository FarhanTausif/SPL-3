from __future__ import annotations

import argparse
import asyncio

from dehalu.adapters.language import build_language_registry
from dehalu.adapters.llm.fake import FakeLLMProvider
from dehalu.agents.contracts import CrewExecutionContext
from dehalu.agents.runner import CrewAIRunner
from dehalu.agents.task_specs import create_all_task_specs
from dehalu.agents.workflow import (
    WorkflowExecutor,
    build_advanced_execution_workflow,
    build_linear_workflow,
    build_repair_aware_workflow,
    estimate_workflow_duration,
    get_workflow_summary,
)
from dehalu.orchestration.execution import _ExecutionStages
from dehalu.schemas import NormalizedRequest, RiskLevel, RunMode
from dehalu.verification.claims import ClaimExtractor
from dehalu.verification.policy import PolicyEngine
from dehalu.verification.sandbox import SandboxVerifier
from dehalu.verification.static_analysis import StaticAnalyzer


def _build_stages() -> _ExecutionStages:
    language_registry = build_language_registry()
    return _ExecutionStages(
        claim_extractor=ClaimExtractor(language_registry),
        static_analyzer=StaticAnalyzer(language_registry),
        sandbox_verifier=SandboxVerifier(),
        policy_engine=PolicyEngine(),
    )


def _build_request() -> NormalizedRequest:
    return NormalizedRequest(
        prompt="Write a Python function that computes square root using math.sqrt.",
        language="python",
        risk_level=RiskLevel.low,
        latency_budget_seconds=15,
        provider="fake",
        run_mode=RunMode.basic,
        target_runtime="python3.12",
        framework_hint="standard",
        acceptance_criteria=["Use math.sqrt", "Return float output"],
    )


def _build_workflow(kind: str, task_specs):
    if kind == "linear":
        return build_linear_workflow(task_specs)
    if kind == "repair":
        return build_repair_aware_workflow(task_specs)
    return build_advanced_execution_workflow(task_specs)


async def run_once(workflow_kind: str) -> None:
    provider = FakeLLMProvider()
    stages = _build_stages()
    task_specs = create_all_task_specs(stages)
    workflow = _build_workflow(workflow_kind, task_specs)

    context = CrewExecutionContext(
        normalized_request=_build_request(),
        provider=provider,
        orchestration_mode="crewai",
    )

    runner = CrewAIRunner()
    executor = WorkflowExecutor(workflow=workflow, runner=runner, context=context)
    await executor.execute()

    print(get_workflow_summary(workflow))
    print(f"Estimated duration (ms): {estimate_workflow_duration(workflow)}")
    print(f"Final policy decision: {context.policy_decision.state.value if context.policy_decision else 'none'}")
    print(f"Trace entries: {len(context.trace)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run DeHalu CrewAI workflow example with fake provider.")
    parser.add_argument(
        "--workflow",
        choices=["linear", "repair", "advanced"],
        default="linear",
        help="Workflow type to execute.",
    )
    args = parser.parse_args()
    asyncio.run(run_once(args.workflow))
