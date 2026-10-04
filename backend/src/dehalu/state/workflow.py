"""Durable queue and event journal; all state transitions use short transactions."""
from datetime import datetime, timedelta, timezone
from uuid import UUID
from sqlalchemy import select, func, update
from sqlalchemy.orm import Session
from dehalu.domain.models import RunCreate
from dehalu.state.models import RunRecord, RunEventRecord, RunJobRecord
from dehalu.state.repository import RunRepository, run_to_summary
from dehalu.verification.inference import infer_prompt
from dehalu.core.settings import settings

TERMINAL = {'completed', 'rejected', 'failed', 'cancelled', 'interrupted', 'needs_clarification', 'reject'}


class RunStopped(Exception): pass


def journal(db: Session, run_id: str, event: dict, *, allow_terminal=False):
    db.flush()
    run = db.scalar(select(RunRecord).where(RunRecord.id == UUID(run_id)).with_for_update().execution_options(populate_existing=True))
    if not run: raise LookupError('Run not found')
    if run.status in {'cancelled', 'interrupted'} and not allow_terminal:
        db.rollback()
        raise RunStopped(run.status)
    if event['type'] == 'stage':
        run.run_metadata = {**run.run_metadata, 'current_stage': event.get('stage') if event.get('status') == 'running' else None}
    sequence = (db.scalar(select(func.max(RunEventRecord.sequence)).where(RunEventRecord.run_id == run.id)) or 0) + 1
    now = datetime.now(timezone.utc)
    payload = {**event, 'run_id': run_id, 'sequence': sequence, 'timestamp': now.isoformat()}
    db.add(RunEventRecord(run_id=run.id, sequence=sequence, timestamp=now, event_type=event['type'], payload=payload))
    db.commit()
    return payload


def enqueue(db: Session, request: RunCreate):
    inference = infer_prompt(request.prompt, request.language_hint, request.constraints)
    repo = RunRepository(db)
    run = repo.create_run(request.prompt, settings.ollama_model, request.max_retry if request.max_retry is not None else settings.default_max_retry, inference)
    run.status = 'queued'
    run.run_metadata = {**run.run_metadata, 'request': request.model_dump(), 'config': {'model': settings.ollama_model, 'max_retry': run.max_retry, 'metric_version': '2.0', 'catalog_version': '2026.1', 'fake_mode': settings.allow_fake_llm, 'package_lookups': settings.package_lookups}, 'provenance': 'implementation-v2'}
    db.add(RunJobRecord(run_id=run.id, status='queued'))
    journal(db, str(run.id), {'type': 'run_created', 'inferred': inference.model_dump(), 'model_name': run.model_name})
    return run_to_summary(repo.get_run(str(run.id)))


def claim_job(db: Session, owner: str):
    job = db.scalar(select(RunJobRecord).where(RunJobRecord.status == 'queued').order_by(RunJobRecord.created_at).with_for_update(skip_locked=True).limit(1))
    if not job:
        db.rollback()
        return None
    job.status = 'running'
    job.owner = owner
    job.lease_until = datetime.now(timezone.utc) + timedelta(seconds=settings.worker_lease_seconds)
    run = db.get(RunRecord, job.run_id)
    run.status = 'running'
    db.commit()
    return str(job.run_id)


def heartbeat(db: Session, run_id: str, owner: str):
    result = db.execute(update(RunJobRecord).where(RunJobRecord.run_id == UUID(run_id), RunJobRecord.owner == owner, RunJobRecord.status == 'running').values(lease_until=datetime.now(timezone.utc) + timedelta(seconds=settings.worker_lease_seconds)))
    db.commit()
    return result.rowcount == 1


def finish(db: Session, run_id: str, status: str, error: str | None = None):
    run = db.scalar(select(RunRecord).where(RunRecord.id == UUID(run_id)).with_for_update().execution_options(populate_existing=True))
    if run.status in {'cancelled', 'interrupted'} and status not in {'cancelled', 'interrupted'}:
        db.rollback()
        raise RunStopped(run.status)
    run.status = status
    run.completed_at = None if status == 'needs_clarification' else datetime.now(timezone.utc)
    if error: run.run_metadata = {**run.run_metadata, 'error': error}
    db.execute(update(RunJobRecord).where(RunJobRecord.run_id == run.id).values(status=status, lease_until=None))
    db.commit()


def cancel(db: Session, run_id: str):
    run = db.scalar(select(RunRecord).where(RunRecord.id == UUID(run_id)).with_for_update().execution_options(populate_existing=True))
    if run.status in TERMINAL - {'needs_clarification'}:
        db.rollback()
        return
    run.status = 'cancelled'
    run.completed_at = datetime.now(timezone.utc)
    db.execute(update(RunJobRecord).where(RunJobRecord.run_id == run.id).values(status='cancelled', lease_until=None))
    db.commit()
    journal(db, run_id, {'type': 'run_cancelled'}, allow_terminal=True)


def resume(db: Session, run_id: str, answers: str, language_hint: str | None):
    run = db.scalar(select(RunRecord).where(RunRecord.id == UUID(run_id)).with_for_update().execution_options(populate_existing=True))
    if run.status != 'needs_clarification':
        db.rollback()
        raise ValueError('Run is not waiting for clarification')
    request = RunCreate.model_validate(run.run_metadata['request'])
    request.prompt += '\nClarification: ' + answers
    if language_hint: request.language_hint = language_hint
    run.run_metadata = {**run.run_metadata, 'request': request.model_dump(), 'error': None}
    run.status = 'queued'
    run.completed_at = None
    db.execute(update(RunJobRecord).where(RunJobRecord.run_id == run.id).values(status='queued', owner=None, lease_until=None))
    db.commit()
    journal(db, run_id, {'type': 'run_resumed'})


def sweep_expired(db: Session):
    jobs = db.scalars(select(RunJobRecord).where(RunJobRecord.status == 'running', RunJobRecord.lease_until < datetime.now(timezone.utc)).with_for_update(skip_locked=True)).all()
    ids = []
    for job in jobs:
        job.status = 'interrupted'
        run = db.get(RunRecord, job.run_id)
        if run.status == 'running':
            run.status = 'interrupted'
            run.completed_at = datetime.now(timezone.utc)
            run.run_metadata = {**run.run_metadata, 'error': 'Worker lease expired. Existing evidence retained; start a new run to retry.'}
            ids.append(str(run.id))
    db.commit()
    for run_id in ids: journal(db, run_id, {'type': 'run_interrupted'}, allow_terminal=True)
    return ids
