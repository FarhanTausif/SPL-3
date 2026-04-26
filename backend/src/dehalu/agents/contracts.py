from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from dehalu.adapters.llm.base import LLMProvider
from dehalu.schemas import (
    CoderOutput,
    CoVeResult,
    ExtractedClaim,
    JudgeResult,
    NormalizedRequest,
    OrchestrationTraceEntry,
    PolicyDecision,
    RepairResult,
    SandboxResult,
    StaticFinding,
)
from dehalu.state.repository import EvaluationBundle


@dataclass(slots=True)
class CrewTaskSpec:
    name: str
    stage: str
    description: str
    expected_output: str
    agent_role: str
    output_key: str | None
    run: Callable[["CrewExecutionContext"], None]
    depends_on: tuple[str, ...] = ()
    audit_label: str | None = None
    should_run: Callable[["CrewExecutionContext"], tuple[bool, str | None]] | None = None


@dataclass(slots=True)
class CrewExecutionContext:
    normalized_request: NormalizedRequest
    provider: LLMProvider
    orchestration_mode: str
    attempt_number: int = 1
    attempt_stage: str = "original"
    generated_output: CoderOutput | None = None
    extracted_claims: list[ExtractedClaim] = field(default_factory=list)
    static_findings: list[StaticFinding] = field(default_factory=list)
    sandbox_result: SandboxResult | None = None
    judge_result: JudgeResult | None = None
    cove_result: CoVeResult | None = None
    policy_decision: PolicyDecision | None = None
    initial_attempt: EvaluationBundle | None = None
    final_attempt: EvaluationBundle | None = None
    repair_result: RepairResult | None = None
    artifacts: dict[str, Any] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    trace: list[OrchestrationTraceEntry] = field(default_factory=list)

    def set_artifact(self, key: str, value: Any) -> None:
        self.artifacts[key] = value

    def has_artifact(self, key: str) -> bool:
        return key in self.artifacts

    def get_artifact(self, key: str, default: Any | None = None) -> Any:
        return self.artifacts.get(key, default)

    def reset_attempt_state(
        self,
        *,
        attempt_number: int,
        attempt_stage: str,
        generated_output: CoderOutput,
    ) -> None:
        self.attempt_number = attempt_number
        self.attempt_stage = attempt_stage
        self.generated_output = generated_output
        self.extracted_claims = []
        self.static_findings = []
        self.sandbox_result = None
        self.judge_result = None
        self.cove_result = None
        self.policy_decision = None

    def record_trace(
        self,
        *,
        task_name: str,
        stage: str,
        agent_role: str,
        status: str,
        output_key: str | None = None,
        audit_label: str | None = None,
        detail: str | None = None,
    ) -> None:
        self.trace.append(
            OrchestrationTraceEntry(
                sequence=len(self.trace) + 1,
                task_name=task_name,
                stage=stage,
                agent_role=agent_role,
                status=status,
                attempt_number=self.attempt_number,
                attempt_stage=self.attempt_stage,
                output_key=output_key,
                audit_label=audit_label,
                detail=detail,
            )
        )
