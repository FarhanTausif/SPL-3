"""Durable jobs, replayable events and versioned structured evidence."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg
revision = '0002_durable_workflow'
down_revision = '0001_initial'
branch_labels = depends_on = None


def upgrade():
    op.add_column('generated_outputs', sa.Column('evidence_payload', pg.JSONB(), nullable=True))
    op.create_unique_constraint('uq_output_attempt', 'generated_outputs', ['run_id', 'attempt_no'])
    op.create_unique_constraint('uq_metric_output', 'metric_results', ['output_id'])
    op.create_unique_constraint('uq_consensus_output', 'judge_consensus', ['output_id'])
    for table, field in [('metric_results', 'entropy_score'), ('judge_results', 'score'), ('judge_consensus', 'average_score')]:
        op.alter_column(table, field, existing_type=sa.Float(), nullable=True)
    op.execute("UPDATE runs SET run_metadata = run_metadata || '{\"provenance\": \"legacy-prototype\"}'::jsonb")
    op.create_table('run_jobs', sa.Column('id', pg.UUID(as_uuid=True), primary_key=True),
        sa.Column('run_id', pg.UUID(as_uuid=True), sa.ForeignKey('runs.id'), nullable=False, unique=True),
        sa.Column('status', sa.String(32), nullable=False), sa.Column('owner', sa.String(128)),
        sa.Column('lease_until', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index('ix_run_jobs_status', 'run_jobs', ['status'])
    op.create_table('run_events', sa.Column('id', pg.UUID(as_uuid=True), primary_key=True),
        sa.Column('run_id', pg.UUID(as_uuid=True), sa.ForeignKey('runs.id'), nullable=False),
        sa.Column('sequence', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('event_type', sa.String(64), nullable=False), sa.Column('payload', pg.JSONB(), nullable=False),
        sa.UniqueConstraint('run_id', 'sequence', name='uq_run_event_sequence'))
    op.create_index('ix_run_events_run_id', 'run_events', ['run_id'])


def downgrade():
    op.drop_table('run_events')
    op.drop_table('run_jobs')
    op.drop_constraint('uq_consensus_output', 'judge_consensus')
    op.drop_constraint('uq_metric_output', 'metric_results')
    op.drop_constraint('uq_output_attempt', 'generated_outputs')
    op.drop_column('generated_outputs', 'evidence_payload')
    # Nullable scores remain nullable to preserve unavailable evidence on downgrade.
