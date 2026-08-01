from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_active", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sessions.id"), nullable=True),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("inferred_language", sa.String(64), nullable=True),
        sa.Column("model_name", sa.String(128), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("max_retry", sa.Integer(), nullable=False),
        sa.Column("run_metadata", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "generated_outputs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("runs.id"), nullable=False),
        sa.Column("attempt_no", sa.Integer(), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("entropy_summary", postgresql.JSONB(), nullable=False),
        sa.Column("logprob_summary", postgresql.JSONB(), nullable=False),
    )
    op.create_table(
        "claims",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("output_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("generated_outputs.id"), nullable=False),
        sa.Column("claim_type", sa.String(64), nullable=False),
        sa.Column("claim_text", sa.Text(), nullable=False),
        sa.Column("location", sa.String(128), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
    )
    op.create_table(
        "static_findings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("output_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("generated_outputs.id"), nullable=False),
        sa.Column("rule_id", sa.String(128), nullable=False),
        sa.Column("severity", sa.String(32), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("location", sa.String(128), nullable=False),
        sa.Column("evidence_source", sa.String(128), nullable=False),
    )
    op.create_table(
        "metric_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("output_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("generated_outputs.id"), nullable=False),
        sa.Column("mihn", sa.Float(), nullable=False),
        sa.Column("mahr", sa.Float(), nullable=False),
        sa.Column("tr_s", sa.Float(), nullable=False),
        sa.Column("entropy_score", sa.Float(), nullable=False),
        sa.Column("hallucination_risk_score", sa.Float(), nullable=False),
    )
    op.create_table(
        "judge_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("output_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("generated_outputs.id"), nullable=False),
        sa.Column("judge_name", sa.String(64), nullable=False),
        sa.Column("judge_model", sa.String(128), nullable=False),
        sa.Column("verdict", sa.String(32), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("rubric_json", postgresql.JSONB(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "judge_consensus",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("output_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("generated_outputs.id"), nullable=False),
        sa.Column("final_verdict", sa.String(32), nullable=False),
        sa.Column("average_score", sa.Float(), nullable=False),
        sa.Column("agreement_level", sa.String(32), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
    )
    op.create_table(
        "cove_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("output_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("generated_outputs.id"), nullable=False),
        sa.Column("claim_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("claims.id"), nullable=True),
        sa.Column("verdict", sa.String(32), nullable=False),
        sa.Column("evidence", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
    )
    op.create_table(
        "policy_decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("runs.id"), nullable=False),
        sa.Column("output_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("generated_outputs.id"), nullable=True),
        sa.Column("decision", sa.String(32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    for table in [
        "policy_decisions",
        "cove_results",
        "judge_consensus",
        "judge_results",
        "metric_results",
        "static_findings",
        "claims",
        "generated_outputs",
        "runs",
        "sessions",
    ]:
        op.drop_table(table)
