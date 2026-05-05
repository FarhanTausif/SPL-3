"""runs events and verification fields

Revision ID: 0003_runs_events_and_verification_fields
Revises: 0002_worker_lifecycle_and_leases
Create Date: 2026-05-06
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0003_runs_events_fields"
down_revision = "0002_worker_lifecycle_and_leases"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    existing_run_columns = {column["name"] for column in inspector.get_columns("runs")}
    existing_tables = set(inspector.get_table_names())

    with op.batch_alter_table("runs") as batch_op:
        if "clarification_result" not in existing_run_columns:
            batch_op.add_column(sa.Column("clarification_result", sa.JSON(), nullable=True))
        if "fused_metrics" not in existing_run_columns:
            batch_op.add_column(sa.Column("fused_metrics", sa.JSON(), nullable=True))
        if "stage_summary" not in existing_run_columns:
            batch_op.add_column(sa.Column("stage_summary", sa.JSON(), nullable=True))

    if "run_events" not in existing_tables:
        op.create_table(
            "run_events",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("run_id", sa.String(length=36), sa.ForeignKey("runs.id"), nullable=False),
            sa.Column("sequence", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("event_type", sa.String(length=64), nullable=False),
            sa.Column("stage", sa.String(length=64), nullable=False),
            sa.Column("status", sa.String(length=64), nullable=False),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column("payload", sa.JSON(), nullable=False),
        )
        op.create_index("ix_run_events_run_id", "run_events", ["run_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "run_events" in existing_tables:
        op.drop_index("ix_run_events_run_id", table_name="run_events")
        op.drop_table("run_events")

    existing_run_columns = {column["name"] for column in inspector.get_columns("runs")}
    with op.batch_alter_table("runs") as batch_op:
        if "stage_summary" in existing_run_columns:
            batch_op.drop_column("stage_summary")
        if "fused_metrics" in existing_run_columns:
            batch_op.drop_column("fused_metrics")
        if "clarification_result" in existing_run_columns:
            batch_op.drop_column("clarification_result")