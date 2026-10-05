"""Explicit local smoke check using configured real providers and an isolated DB.

Run only with DATABASE_URL pointing at a disposable, migrated database.
Generated code is persisted and statically analyzed; it is never executed.
"""
import json
from dehalu.domain.models import RunCreate
from dehalu.state.database import SessionLocal
from dehalu.state.workflow import enqueue
from dehalu.services.pipeline import DeHaluPipeline
from dehalu.core.settings import settings

if settings.allow_fake_llm:
    raise SystemExit('Real-provider smoke check requires DEHALU_ALLOW_FAKE_LLM=false')
with SessionLocal() as db:
    pipeline = DeHaluPipeline(db)
    run = enqueue(db, RunCreate(prompt='Write a Python function add(a, b) that returns the sum of its two numeric arguments. Use no dependencies.', language_hint='python', max_retry=1))
    for event in pipeline._drive(run.id):
        if event['type'] == 'stage' and event['status'] == 'running': print(event['stage'], flush=True)
    evidence = pipeline.get_evidence(run.id)
    print(json.dumps({'run_id': run.id, 'status': evidence.run.status, 'error': evidence.run.error, 'attempts': [
        {'policy': attempt.policy.model_dump(), 'claims': [(c.claim_type, c.status) for c in attempt.claims],
         'coverage': [c.model_dump() for c in attempt.coverage], 'judges': [j.model_dump() for j in attempt.judge_results]}
        for attempt in evidence.attempts]}, indent=2))
