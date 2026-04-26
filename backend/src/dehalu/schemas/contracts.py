from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RiskLevel(StrEnum):
    low = "low"
    medium = "medium"
    high = "high"


class StaticFindingSeverity(StrEnum):
    info = "info"
    warning = "warning"
    error = "error"


class SandboxStatus(StrEnum):
    passed = "passed"
    failed = "failed"
    unsupported = "unsupported"


class JudgeVerdict(StrEnum):
    pass_ = "pass"
    uncertain = "uncertain"
    fail = "fail"


class CoVeVerdict(StrEnum):
    pass_ = "pass"
    uncertain = "uncertain"
    fail = "fail"


class CoVeCheckVerdict(StrEnum):
    supported = "supported"
    uncertain = "uncertain"
    unsupported = "unsupported"


class RepairOutcome(StrEnum):
    attempted = "attempted"
    succeeded = "succeeded"
    failed = "failed"
    skipped = "skipped"


class RepairTrigger(StrEnum):
    judge_fail = "judge_fail"
    judge_uncertain = "judge_uncertain"
    cove_fail = "cove_fail"
    cove_uncertain = "cove_uncertain"


class PolicyDecisionState(StrEnum):
    accept = "accept"
    warn_and_return_partial = "warn_and_return_partial"
    reject = "reject"
    repair_and_retry = "repair_and_retry"
    clarify = "clarify"


class EvidenceKind(StrEnum):
    claim_extraction = "claim_extraction"
    static_analysis = "static_analysis"
    sandbox = "sandbox"
    judge = "judge"
    cove = "cove"
    repair = "repair"
    policy = "policy"
    orchestration = "orchestration"


class RunRequest(BaseModel):
    prompt: str = Field(min_length=1)
    language_hint: str | None = None
    risk_level: RiskLevel = RiskLevel.medium
    latency_budget_seconds: int = Field(default=15, ge=1, le=120)
    provider: str | None = None

    @field_validator("prompt")
    @classmethod
    def strip_prompt(cls, value: str) -> str:
        prompt = value.strip()
        if not prompt:
            raise ValueError("prompt must not be blank")
        return prompt

    @field_validator("language_hint", "provider")
    @classmethod
    def normalize_optional_token(cls, value: str | None) -> str | None:
        if value is None:
            return None
        token = value.strip().lower()
        return token or None


class NormalizedRequest(BaseModel):
    prompt: str
    language: str
    risk_level: RiskLevel
    latency_budget_seconds: int
    provider: str


class CoderOutput(BaseModel):
    provider: str
    model: str
    language: str
    code: str
    assumptions: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    files_touched: list[str] = Field(default_factory=list)
    execution_notes: list[str] = Field(default_factory=list)


class ExtractedClaim(BaseModel):
    kind: str
    value: str
    source: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class StaticFinding(BaseModel):
    code: str
    message: str
    severity: StaticFindingSeverity
    line: int | None = None
    column: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SandboxResult(BaseModel):
    status: SandboxStatus
    check_type: str
    language: str
    duration_ms: float = Field(ge=0.0)
    findings: list[StaticFinding] = Field(default_factory=list)


class JudgeFinding(BaseModel):
    code: str
    message: str
    severity: StaticFindingSeverity
    claim: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class JudgeResult(BaseModel):
    verdict: JudgeVerdict
    provider: str
    model: str
    duration_ms: float = Field(ge=0.0)
    hallucination_score: float = Field(ge=0.0, le=1.0)
    findings: list[JudgeFinding] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)


class CoVeClaimCheck(BaseModel):
    claim: str
    question: str
    answer: str | None = None
    verdict: CoVeCheckVerdict
    metadata: dict[str, Any] = Field(default_factory=dict)


class CoVeFinding(BaseModel):
    code: str
    message: str
    severity: StaticFindingSeverity
    claim: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CoVeResult(BaseModel):
    verdict: CoVeVerdict
    provider: str
    model: str
    duration_ms: float = Field(ge=0.0)
    hallucination_score: float = Field(ge=0.0, le=1.0)
    checks: list[CoVeClaimCheck] = Field(default_factory=list)
    findings: list[CoVeFinding] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)


class RepairAttempt(BaseModel):
    attempt_number: int = Field(ge=1)
    trigger: RepairTrigger
    provider: str
    model: str
    duration_ms: float = Field(ge=0.0)
    input_code: str
    output_code: str | None = None
    summary: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class RepairResult(BaseModel):
    outcome: RepairOutcome
    attempts: list[RepairAttempt] = Field(default_factory=list)
    final_attempt_number: int = Field(ge=1)
    metrics: dict[str, Any] = Field(default_factory=dict)


class VerificationEvidence(BaseModel):
    id: str | None = None
    run_id: str | None = None
    kind: EvidenceKind
    payload: dict[str, Any]
    created_at: datetime | None = None


class OrchestrationTraceEntry(BaseModel):
    sequence: int = Field(ge=1)
    task_name: str
    stage: str
    agent_role: str
    status: str
    attempt_number: int = Field(ge=1)
    attempt_stage: str
    output_key: str | None = None
    audit_label: str | None = None
    detail: str | None = None


class PolicyDecision(BaseModel):
    state: PolicyDecisionState
    reasons: list[str] = Field(default_factory=list)
    hard_fail: bool = False
    score: float = Field(ge=0.0, le=1.0)
    metrics: dict[str, Any] = Field(default_factory=dict)


class RunResponse(BaseModel):
    run_id: str
    normalized_request: NormalizedRequest
    coder_output: CoderOutput
    extracted_claims: list[ExtractedClaim]
    static_findings: list[StaticFinding]
    sandbox_result: SandboxResult
    judge_result: JudgeResult
    cove_result: CoVeResult
    repair_result: RepairResult
    policy_decision: PolicyDecision
    evidence_ids: list[str]


class RunDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    run_id: str
    created_at: datetime
    normalized_request: NormalizedRequest
    policy_decision: PolicyDecision
    evidence_summary: dict[str, int]


class HealthResponse(BaseModel):
    status: str
    version: str
    providers: dict[str, bool]
    orchestration: dict[str, Any] = Field(default_factory=dict)
