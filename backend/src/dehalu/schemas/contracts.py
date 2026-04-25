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
    policy = "policy"


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


class VerificationEvidence(BaseModel):
    id: str | None = None
    run_id: str | None = None
    kind: EvidenceKind
    payload: dict[str, Any]
    created_at: datetime | None = None


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
