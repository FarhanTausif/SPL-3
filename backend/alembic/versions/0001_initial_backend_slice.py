"""initial backend slice

Revision ID: 0001_initial_backend_slice
Revises:
Create Date: 2026-04-26
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0001_initial_backend_slice"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "runs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("language", sa.String(length=64), nullable=False),
        sa.Column("risk_level", sa.String(length=32), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("normalized_request", sa.JSON(), nullable=False),
        sa.Column("coder_output", sa.JSON(), nullable=False),
        sa.Column("policy_decision", sa.JSON(), nullable=False),
    )
    op.create_table(
        "evidence",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("run_id", sa.String(length=36), sa.ForeignKey("runs.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("kind", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
    )
    op.create_index("ix_evidence_run_id", "evidence", ["run_id"])


def downgrade() -> None:
    op.drop_index("ix_evidence_run_id", table_name="evidence")
    op.drop_table("evidence")
    op.drop_table("runs")

