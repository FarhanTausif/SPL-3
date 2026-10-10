"""Transport-independent contracts used by analyzers, orchestration and persistence."""
from __future__ import annotations
from datetime import datetime
from typing import Any, Literal
from uuid import uuid4
from pydantic import BaseModel, Field, model_validator


def identifier() -> str:
    return str(uuid4())


class RunCreate(BaseModel):
    prompt: str = Field(min_length=3, max_length=30000)
    language_hint: str | None = None
    framework_hint: str | None = None
    runtime_hint: str | None = None
    libraries: list[str] = Field(default_factory=list)
    max_retry: int | None = Field(default=None, ge=0, le=5)
    constraints: list[str] = Field(default_factory=list)


class ClarificationAnswers(BaseModel):
    answers: str = Field(default="", max_length=10000)
    language_hint: str | None = None
    skip_clarification: bool = False

    @model_validator(mode="after")
    def answer_or_skip(self):
        if not self.skip_clarification and not self.answers.strip():
            raise ValueError("Provide answers or choose Run Anyway")
        return self


class ClarificationChoice(BaseModel):
    label: str
    value: str
    recommended: bool = False


class ClarificationQuestion(BaseModel):
    question: str
    choices: list[ClarificationChoice] = Field(min_length=3, max_length=3)

    @model_validator(mode="after")
    def one_recommendation(self):
        if sum(choice.recommended for choice in self.choices) != 1:
            raise ValueError("Exactly one choice must be recommended")
        return self


class InferenceResult(BaseModel):
    language: str | None = None
    framework: str | None = None
    runtime: str | None = None
    libraries: list[str] = Field(default_factory=list)
    requirements: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    uncertain_assumptions: list[str] = Field(default_factory=list)
    clarification_questions: list[str] = Field(default_factory=list)
    needs_clarification: bool = False
    clarification_details: list[ClarificationQuestion] = Field(default_factory=list, max_length=3)

    @model_validator(mode="after")
    def questions_match(self):
        if self.needs_clarification != bool(self.clarification_questions):
            raise ValueError("Blocking clarification must include questions")
        return self


class GeneratedOutput(BaseModel):
    id: str = Field(default_factory=identifier)
    attempt_no: int
    code: str
    explanation: str = ""
    provider: str
    entropy_summary: dict[str, Any] = Field(default_factory=lambda: {"available": False})
    logprob_summary: dict[str, Any] = Field(default_factory=lambda: {"available": False})
    metadata: dict[str, Any] = Field(default_factory=dict)
    repair_summary: list[str] = Field(default_factory=list)


class Claim(BaseModel):
    id: str = Field(default_factory=identifier)
    claim_type: str
    claim_text: str
    location: str = ""
    status: Literal["not_checked", "supported", "unsupported", "uncertain"] = "not_checked"
    source_range: dict[str, int] = Field(default_factory=dict)
    check_method: str = "symbol_indexer"
    evidence_ids: list[str] = Field(default_factory=list)
    evidence: str = ""
    details: dict[str, Any] = Field(default_factory=dict)


class StaticFinding(BaseModel):
    id: str = Field(default_factory=identifier)
    rule_id: str
    severity: Literal["info", "warning", "error"]
    message: str
    location: str = ""
    evidence_source: str
    claim_ids: list[str] = Field(default_factory=list)
    source_range: dict[str, int] = Field(default_factory=dict)


class AnalyzerCoverage(BaseModel):
    analyzer: str
    language: str
    status: Literal["available", "partial", "unavailable", "failed"]
    detail: str
    version: str | None = None


class MetricResult(BaseModel):
    mihn: float
    mahr: float
    tr_s: float
    entropy_score: float | None = None
    hallucination_risk_score: float
    static_severity_score: float = 0
    uncertainty_score: float = 0
    unsupported_count: int = 0
    uncertain_count: int = 0
    total_claims: int = 0
    version: str = "2.1"


class JudgeResult(BaseModel):
    judge_name: str
    judge_model: str
    role: str = ""
    status: Literal["ok", "unavailable", "failed", "simulated"] = "ok"
    verdict: Literal["pass", "warn", "fail"] | None = None
    score: float | None = Field(default=None, ge=0, le=1)
    rubric_json: dict[str, Any] = Field(default_factory=dict)
    explanation: str
    blocking_issues: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    repair_suggestions: list[str] = Field(default_factory=list)


class JudgeConsensus(BaseModel):
    final_verdict: Literal["pass", "warn", "fail"]
    average_score: float | None
    agreement_level: str
    summary: str
    valid_count: int = 0
    expected_count: int = 3


class CoVeResult(BaseModel):
    claim_id: str | None = None
    verification_question: str = ""
    verdict: Literal["supported", "unsupported", "uncertain"]
    evidence: str
    evidence_ids: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)


class SemanticClaim(BaseModel):
    claim_type: Literal["behavior", "runtime", "assumption", "safety"]
    claim_text: str = Field(min_length=1)
    location: str = "explanation"


class SemanticClaimsResponse(BaseModel):
    claims: list[SemanticClaim]


class CoVeResponse(BaseModel):
    cove_results: list[CoVeResult]


class PolicyDecision(BaseModel):
    decision: Literal["accept", "warn", "repair", "reject", "needs_clarification"]
    reason: str
    evidence_ids: list[str] = Field(default_factory=list)
    version: str = "2.0"


class AttemptEvidence(BaseModel):
    output: GeneratedOutput
    claims: list[Claim]
    static_findings: list[StaticFinding]
    coverage: list[AnalyzerCoverage] = Field(default_factory=list)
    metrics: MetricResult
    judge_results: list[JudgeResult]
    judge_consensus: JudgeConsensus
    cove_results: list[CoVeResult]
    policy: PolicyDecision


class RunSummary(BaseModel):
    id: str
    status: str
    prompt: str
    inferred: InferenceResult
    model_name: str
    max_retry: int
    created_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None
    final_output: GeneratedOutput | None = None
    policy_decision: PolicyDecision | None = None


class RunEvidence(BaseModel):
    run: RunSummary
    attempts: list[AttemptEvidence]
    partial: dict[str, Any] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    status: str
    database: str
    ollama: dict[str, Any]
    judges: dict[str, Any]
    capabilities: list[AnalyzerCoverage] = Field(default_factory=list)


class RunEvent(BaseModel):
    run_id: str
    sequence: int
    timestamp: datetime
    type: str
    payload: dict[str, Any]
