from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class RunRecord(Base):
    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    prompt: Mapped[str] = mapped_column(Text)
    language: Mapped[str] = mapped_column(String(64))
    risk_level: Mapped[str] = mapped_column(String(32))
    provider: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(64))
    run_mode: Mapped[str] = mapped_column(String(32), default="basic")
    normalized_request: Mapped[dict] = mapped_column(JSON)
    coder_output: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    policy_decision: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    clarification_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    fused_metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    stage_summary: Mapped[list | None] = mapped_column(JSON, nullable=True)

    evidence: Mapped[list[EvidenceRecord]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="EvidenceRecord.created_at",
    )
    events: Mapped[list[EventRecord]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="EventRecord.sequence",
    )


class EvidenceRecord(Base):
    __tablename__ = "evidence"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("runs.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    kind: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JSON)

    run: Mapped[RunRecord] = relationship(back_populates="evidence")


class EventRecord(Base):
    __tablename__ = "run_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("runs.id"), index=True)
    sequence: Mapped[int] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    event_type: Mapped[str] = mapped_column(String(64))
    stage: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(64))
    message: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict] = mapped_column(JSON)

    run: Mapped[RunRecord] = relationship(back_populates="events")
