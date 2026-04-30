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


class RunMode(StrEnum):
    basic = "basic"
    advanced = "advanced"


class RunLifecycleStatus(StrEnum):
    queued = "queued"
    running = "running"
    needs_clarification = "needs_clarification"
    completed = "completed"
    failed = "failed"


class EvidenceKind(StrEnum):
    claim_extraction = "claim_extraction"
    static_analysis = "static_analysis"
    sandbox = "sandbox"
    judge = "judge"
    cove = "cove"
    repair = "repair"
    policy = "policy"
    orchestration = "orchestration"
    clarification = "clarification"
    tool = "tool"
    panel = "panel"
    fusion = "fusion"
    routing = "routing"
    provider_invocation = "provider_invocation"


class AgentRole(StrEnum):
    clarifier = "clarifier"
    coder = "coder"
    judge = "judge"
    cove = "cove"
    repair = "repair"


class ProviderFailureKind(StrEnum):
    none = "none"
    transient_http = "transient_http"
    rate_limited = "rate_limited"
    auth = "auth"
    misconfiguration = "misconfiguration"
    malformed_output = "malformed_output"
    empty_output = "empty_output"
    transport = "transport"
    unknown = "unknown"


class ToolPolicy(BaseModel):
    max_calls_per_role: int = Field(default=3, ge=0, le=20)
    timeout_seconds: float = Field(default=5.0, gt=0.0, le=60.0)
    allow_repo_context: bool = True
    allow_web_lookup: bool = True
    allowed_domains: list[str] = Field(default_factory=list)


class RunRequest(BaseModel):
    prompt: str = Field(min_length=1)
    language_hint: str | None = None
    risk_level: RiskLevel = RiskLevel.medium
    latency_budget_seconds: int = Field(default=15, ge=1, le=120)
    provider: str | None = None
    run_mode: RunMode = RunMode.basic
    target_runtime: str | None = None
    framework_hint: str | None = None
    acceptance_criteria: list[str] = Field(default_factory=list)
    tool_policy: ToolPolicy | None = None

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
    run_mode: RunMode = RunMode.basic
    target_runtime: str | None = None
    framework_hint: str | None = None
    acceptance_criteria: list[str] = Field(default_factory=list)
    tool_policy: ToolPolicy | None = None


class CoderOutput(BaseModel):
    provider: str
    model: str
    language: str
    code: str
    assumptions: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    files_touched: list[str] = Field(default_factory=list)
    execution_notes: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


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


class ClarificationResult(BaseModel):
    clarified_prompt: str
    requested_outcome: str
    language: str
    runtime_assumptions: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)
    ambiguity_flags: list[str] = Field(default_factory=list)
    needs_user_input: bool = False
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ToolInvocationRecord(BaseModel):
    tool_name: str
    agent_role: AgentRole
    inputs: dict[str, Any] = Field(default_factory=dict)
    summary: str
    duration_ms: float = Field(ge=0.0)
    changed_verdict: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProviderInvocationRecord(BaseModel):
    provider_name: str
    model: str
    stage: str
    role: AgentRole
    success: bool
    latency_ms: float = Field(ge=0.0)
    retry_count: int = Field(default=0, ge=0)
    fallback_used: bool = False
    failure_kind: ProviderFailureKind = ProviderFailureKind.none
    prompt_template_version: str = "v1"
    routing_policy_version: str = "v1"
    usage: dict[str, Any] = Field(default_factory=dict)
    request_summary: dict[str, Any] = Field(default_factory=dict)
    response_summary: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PanelVerdict(BaseModel):
    stage: str
    providers: list[str] = Field(default_factory=list)
    judge_results: list[JudgeResult] = Field(default_factory=list)
    cove_results: list[CoVeResult] = Field(default_factory=list)
    disagreement_score: float = Field(default=0.0, ge=0.0, le=1.0)
    consensus_verdict: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class FusedHallucinationMetrics(BaseModel):
    requirement_alignment_score: float = Field(default=0.5, ge=0.0, le=1.0)
    dependency_plausibility_score: float = Field(default=0.5, ge=0.0, le=1.0)
    api_symbol_validity_score: float = Field(default=0.5, ge=0.0, le=1.0)
    unsupported_assumption_score: float = Field(default=0.5, ge=0.0, le=1.0)
    execution_validity_score: float = Field(default=0.5, ge=0.0, le=1.0)
    judge_disagreement_score: float = Field(default=0.0, ge=0.0, le=1.0)
    tool_supported_claim_ratio: float = Field(default=0.0, ge=0.0, le=1.0)
    overall_hallucination_score: float = Field(default=0.5, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class StageStatus(BaseModel):
    stage: str
    status: str
    started_at: datetime | None = None
    finished_at: datetime | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class RunEvent(BaseModel):
    sequence: int = Field(ge=1)
    event_type: str
    stage: str
    status: str
    message: str
    created_at: datetime | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class PolicyDecision(BaseModel):
    state: PolicyDecisionState
    reasons: list[str] = Field(default_factory=list)
    hard_fail: bool = False
    score: float = Field(ge=0.0, le=1.0)
    metrics: dict[str, Any] = Field(default_factory=dict)


class RunResponse(BaseModel):
    run_id: str
    normalized_request: NormalizedRequest
    status: RunLifecycleStatus = RunLifecycleStatus.completed
    stage_summary: list[StageStatus] = Field(default_factory=list)
    clarification_result: ClarificationResult | None = None
    fused_metrics: FusedHallucinationMetrics | None = None
    coder_output: CoderOutput | None = None
    extracted_claims: list[ExtractedClaim] = Field(default_factory=list)
    static_findings: list[StaticFinding] = Field(default_factory=list)
    sandbox_result: SandboxResult | None = None
    judge_result: JudgeResult | None = None
    cove_result: CoVeResult | None = None
    repair_result: RepairResult | None = None
    policy_decision: PolicyDecision | None = None
    evidence_ids: list[str] = Field(default_factory=list)


class RunDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    run_id: str
    created_at: datetime
    normalized_request: NormalizedRequest
    status: RunLifecycleStatus = RunLifecycleStatus.completed
    policy_decision: PolicyDecision | None = None
    clarification_result: ClarificationResult | None = None
    fused_metrics: FusedHallucinationMetrics | None = None
    stage_summary: list[StageStatus] = Field(default_factory=list)
    evidence_summary: dict[str, int]


class HealthResponse(BaseModel):
    status: str
    version: str
    providers: dict[str, bool]
    orchestration: dict[str, Any] = Field(default_factory=dict)
