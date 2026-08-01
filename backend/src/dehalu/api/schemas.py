from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class RunCreate(BaseModel):
    prompt: str = Field(min_length=3)
    language_hint: str | None = None
    max_retry: int = Field(default=1, ge=0, le=5)
    constraints: list[str] = Field(default_factory=list)


class InferenceResult(BaseModel):
    language: str | None = None
    framework: str | None = None
    runtime: str | None = None
    libraries: list[str] = Field(default_factory=list)
    requirements: list[str] = Field(default_factory=list)
    uncertain_assumptions: list[str] = Field(default_factory=list)
    clarification_questions: list[str] = Field(default_factory=list)
    needs_clarification: bool = False


class GeneratedOutput(BaseModel):
    id: str | None = None
    attempt_no: int
    code: str
    explanation: str = ""
    provider: str
    entropy_summary: dict[str, Any] = Field(default_factory=dict)
    logprob_summary: dict[str, Any] = Field(default_factory=dict)


class Claim(BaseModel):
    id: str | None = None
    claim_type: str
    claim_text: str
    location: str = ""
    status: str = "not_checked"


class StaticFinding(BaseModel):
    rule_id: str
    severity: str
    message: str
    location: str = ""
    evidence_source: str


class MetricResult(BaseModel):
    mihn: float
    mahr: float
    tr_s: float
    entropy_score: float
    hallucination_risk_score: float


class JudgeResult(BaseModel):
    judge_name: str
    judge_model: str
    verdict: str
    score: float
    rubric_json: dict[str, Any] = Field(default_factory=dict)
    explanation: str


class JudgeConsensus(BaseModel):
    final_verdict: str
    average_score: float
    agreement_level: str
    summary: str


class CoVeResult(BaseModel):
    claim_id: str | None = None
    verdict: str
    evidence: str
    confidence: float


class PolicyDecision(BaseModel):
    decision: str
    reason: str


class AttemptEvidence(BaseModel):
    output: GeneratedOutput
    claims: list[Claim]
    static_findings: list[StaticFinding]
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
    final_output: GeneratedOutput | None = None
    policy_decision: PolicyDecision | None = None


class RunEvidence(BaseModel):
    run: RunSummary
    attempts: list[AttemptEvidence]


class HealthResponse(BaseModel):
    status: str
    database: str
    ollama: dict[str, Any]
    judges: dict[str, Any]
