from __future__ import annotations

from datetime import datetime
import uuid

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from dehalu.state.database import Base


def uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class SessionRecord(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = uuid_pk()
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_active: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    runs: Mapped[list[RunRecord]] = relationship(back_populates="session")


class RunRecord(Base):
    __tablename__ = "runs"

    id: Mapped[uuid.UUID] = uuid_pk()
    session_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("sessions.id"), nullable=True)
    prompt: Mapped[str] = mapped_column(Text)
    inferred_language: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model_name: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32), default="created")
    max_retry: Mapped[int] = mapped_column(Integer, default=1)
    run_metadata: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    session: Mapped[SessionRecord | None] = relationship(back_populates="runs")
    outputs: Mapped[list[GeneratedOutputRecord]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    policy_decisions: Mapped[list[PolicyDecisionRecord]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class GeneratedOutputRecord(Base):
    __tablename__ = "generated_outputs"
    __table_args__ = (UniqueConstraint("run_id", "attempt_no", name="uq_output_attempt"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("runs.id"), nullable=False)
    attempt_no: Mapped[int] = mapped_column(Integer)
    code: Mapped[str] = mapped_column(Text)
    explanation: Mapped[str] = mapped_column(Text, default="")
    evidence_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    provider: Mapped[str] = mapped_column(String(64))
    entropy_summary: Mapped[dict] = mapped_column(JSONB, default=dict)
    logprob_summary: Mapped[dict] = mapped_column(JSONB, default=dict)

    run: Mapped[RunRecord] = relationship(back_populates="outputs")
    claims: Mapped[list[ClaimRecord]] = relationship(back_populates="output", cascade="all, delete-orphan")
    static_findings: Mapped[list[StaticFindingRecord]] = relationship(
        back_populates="output", cascade="all, delete-orphan"
    )
    metric_result: Mapped[MetricResultRecord | None] = relationship(
        back_populates="output", cascade="all, delete-orphan", uselist=False
    )
    judge_results: Mapped[list[JudgeResultRecord]] = relationship(
        back_populates="output", cascade="all, delete-orphan"
    )
    judge_consensus: Mapped[JudgeConsensusRecord | None] = relationship(
        back_populates="output", cascade="all, delete-orphan", uselist=False
    )
    cove_results: Mapped[list[CoVeResultRecord]] = relationship(
        back_populates="output", cascade="all, delete-orphan"
    )
    policy_decisions: Mapped[list[PolicyDecisionRecord]] = relationship(
        back_populates="output", cascade="all, delete-orphan"
    )


class ClaimRecord(Base):
    __tablename__ = "claims"

    id: Mapped[uuid.UUID] = uuid_pk()
    output_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("generated_outputs.id"), nullable=False)
    claim_type: Mapped[str] = mapped_column(String(64))
    claim_text: Mapped[str] = mapped_column(Text)
    location: Mapped[str] = mapped_column(String(128), default="")
    status: Mapped[str] = mapped_column(String(32), default="not_checked")

    output: Mapped[GeneratedOutputRecord] = relationship(back_populates="claims")
    cove_results: Mapped[list[CoVeResultRecord]] = relationship(back_populates="claim")


class StaticFindingRecord(Base):
    __tablename__ = "static_findings"

    id: Mapped[uuid.UUID] = uuid_pk()
    output_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("generated_outputs.id"), nullable=False)
    rule_id: Mapped[str] = mapped_column(String(128))
    severity: Mapped[str] = mapped_column(String(32))
    message: Mapped[str] = mapped_column(Text)
    location: Mapped[str] = mapped_column(String(128), default="")
    evidence_source: Mapped[str] = mapped_column(String(128))

    output: Mapped[GeneratedOutputRecord] = relationship(back_populates="static_findings")


class MetricResultRecord(Base):
    __tablename__ = "metric_results"
    __table_args__ = (UniqueConstraint("output_id", name="uq_metric_output"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    output_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("generated_outputs.id"), nullable=False)
    mihn: Mapped[float] = mapped_column(Float)
    mahr: Mapped[float] = mapped_column(Float)
    tr_s: Mapped[float] = mapped_column(Float)
    entropy_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    hallucination_risk_score: Mapped[float] = mapped_column(Float)

    output: Mapped[GeneratedOutputRecord] = relationship(back_populates="metric_result")


class JudgeResultRecord(Base):
    __tablename__ = "judge_results"

    id: Mapped[uuid.UUID] = uuid_pk()
    output_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("generated_outputs.id"), nullable=False)
    judge_name: Mapped[str] = mapped_column(String(64))
    judge_model: Mapped[str] = mapped_column(String(128))
    verdict: Mapped[str] = mapped_column(String(32))
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    rubric_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    explanation: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    output: Mapped[GeneratedOutputRecord] = relationship(back_populates="judge_results")


class JudgeConsensusRecord(Base):
    __tablename__ = "judge_consensus"
    __table_args__ = (UniqueConstraint("output_id", name="uq_consensus_output"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    output_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("generated_outputs.id"), nullable=False)
    final_verdict: Mapped[str] = mapped_column(String(32))
    average_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    agreement_level: Mapped[str] = mapped_column(String(32))
    summary: Mapped[str] = mapped_column(Text)

    output: Mapped[GeneratedOutputRecord] = relationship(back_populates="judge_consensus")


class CoVeResultRecord(Base):
    __tablename__ = "cove_results"

    id: Mapped[uuid.UUID] = uuid_pk()
    output_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("generated_outputs.id"), nullable=False)
    claim_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("claims.id"), nullable=True)
    verdict: Mapped[str] = mapped_column(String(32))
    evidence: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float)

    output: Mapped[GeneratedOutputRecord] = relationship(back_populates="cove_results")
    claim: Mapped[ClaimRecord | None] = relationship(back_populates="cove_results")


class PolicyDecisionRecord(Base):
    __tablename__ = "policy_decisions"

    id: Mapped[uuid.UUID] = uuid_pk()
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("runs.id"), nullable=False)
    output_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("generated_outputs.id"), nullable=True)
    decision: Mapped[str] = mapped_column(String(32))
    reason: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    run: Mapped[RunRecord] = relationship(back_populates="policy_decisions")
    output: Mapped[GeneratedOutputRecord | None] = relationship(back_populates="policy_decisions")


class RunJobRecord(Base):
    __tablename__ = "run_jobs"
    id: Mapped[uuid.UUID] = uuid_pk()
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("runs.id"), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="queued", index=True)
    owner: Mapped[str | None] = mapped_column(String(128), nullable=True)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RunEventRecord(Base):
    __tablename__ = "run_events"
    __table_args__ = (UniqueConstraint("run_id", "sequence", name="uq_run_event_sequence"),)
    id: Mapped[uuid.UUID] = uuid_pk()
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("runs.id"), nullable=False, index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    event_type: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JSONB)
