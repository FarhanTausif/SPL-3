"""worker lifecycle and leases

Revision ID: 0002_worker_lifecycle_and_leases
Revises: 0001_initial_backend_slice
Create Date: 2026-04-26
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0002_worker_lifecycle_and_leases"
down_revision = "0001_initial_backend_slice"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("runs", sa.Column("run_mode", sa.String(length=32), nullable=False, server_default="basic"))
    op.add_column("runs", sa.Column("queued_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("runs", sa.Column("started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("runs", sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("runs", sa.Column("claimed_by", sa.String(length=128), nullable=True))
    op.add_column("runs", sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("runs", sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("runs", sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("runs", sa.Column("last_error", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("runs", "last_error")
    op.drop_column("runs", "attempt_count")
    op.drop_column("runs", "lease_expires_at")
    op.drop_column("runs", "last_heartbeat_at")
    op.drop_column("runs", "claimed_by")
    op.drop_column("runs", "completed_at")
    op.drop_column("runs", "started_at")
    op.drop_column("runs", "queued_at")
    op.drop_column("runs", "run_mode")
