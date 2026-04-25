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
    normalized_request: Mapped[dict] = mapped_column(JSON)
    coder_output: Mapped[dict] = mapped_column(JSON)
    policy_decision: Mapped[dict] = mapped_column(JSON)

    evidence: Mapped[list[EvidenceRecord]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="EvidenceRecord.created_at",
    )


class EvidenceRecord(Base):
    __tablename__ = "evidence"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("runs.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    kind: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JSON)

    run: Mapped[RunRecord] = relationship(back_populates="evidence")

