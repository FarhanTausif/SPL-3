from __future__ import annotations
import asyncio
import json
from uuid import UUID
import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool
from dehalu.domain.models import ClarificationAnswers, HealthResponse, RunCreate, RunEvidence, RunSummary
from dehalu.core.settings import settings
from dehalu.services.pipeline import DeHaluPipeline
from dehalu.state.database import SessionLocal, get_session
from dehalu.state.models import RunRecord, RunEventRecord
from dehalu.state.repository import RunRepository, run_to_summary
from dehalu.state.workflow import TERMINAL, enqueue, cancel, resume
from dehalu.verification.adapters import REGISTRY

router = APIRouter(prefix='/api')


@router.get('/health', response_model=HealthResponse)
def health(db: Session = Depends(get_session)):
    database = 'ok'
    try: db.execute(text('select 1'))
    except Exception:
        db.rollback()
        database = 'unavailable'
    ollama = {'model': settings.ollama_model, 'fake_mode': settings.allow_fake_llm, 'reachable': False, 'model_available': False}
    if not settings.allow_fake_llm:
        try:
            response = httpx.get(f'{settings.ollama_base_url.rstrip("/")}/api/tags', timeout=2)
            response.raise_for_status()
            models = [item['name'] for item in response.json()['models']]
            ollama.update(reachable=True, model_available=settings.ollama_model in models)
        except (httpx.HTTPError, ValueError, KeyError): pass
    judges = {name: {'configured': bool(key), 'model': model, 'readiness': 'configured_unchecked' if key else 'unavailable'} for name, key, model in [
        ('gemini', settings.gemini_api_key, settings.gemini_model), ('groq', settings.groq_api_key, settings.groq_model), ('mistral', settings.mistral_api_key, settings.mistral_model)]}
    coverage = [c for adapter in REGISTRY.values() for c in adapter.coverage()]
    return HealthResponse(status='ok' if database == 'ok' and ollama['model_available'] and all(j['configured'] for j in judges.values()) else 'degraded', database=database, ollama=ollama, judges=judges, capabilities=coverage)


@router.post('/runs', response_model=RunSummary, status_code=202)
def create_run(request: RunCreate, db: Session = Depends(get_session)):
    return enqueue(db, request)


@router.get('/runs', response_model=list[RunSummary])
def list_runs(limit: int = Query(30, ge=1, le=100), offset: int = Query(0, ge=0), db: Session = Depends(get_session)):
    ids = db.scalars(select(RunRecord.id).order_by(RunRecord.created_at.desc()).offset(offset).limit(limit)).all()
    repo = RunRepository(db)
    return [run_to_summary(repo.get_run(str(run_id))) for run_id in ids]


def require_run(db, run_id):
    run = RunRepository(db).get_run(str(run_id))
    if not run: raise HTTPException(404, 'Run not found')
    return run


@router.get('/runs/{run_id}', response_model=RunSummary)
def get_run(run_id: UUID, db: Session = Depends(get_session)):
    return run_to_summary(require_run(db, run_id))


@router.get('/runs/{run_id}/evidence', response_model=RunEvidence)
def get_evidence(run_id: UUID, db: Session = Depends(get_session)):
    require_run(db, run_id)
    return DeHaluPipeline(db).get_evidence(str(run_id))


@router.get('/runs/{run_id}/export', response_model=RunEvidence)
def export_run(run_id: UUID, db: Session = Depends(get_session)):
    require_run(db, run_id)
    evidence = DeHaluPipeline(db).get_evidence(str(run_id))
    return JSONResponse(evidence.model_dump(mode='json'), headers={'Content-Disposition': f'attachment; filename="dehalu-{run_id}.json"'})


@router.post('/runs/{run_id}/cancel', response_model=RunSummary)
def cancel_run(run_id: UUID, db: Session = Depends(get_session)):
    require_run(db, run_id)
    cancel(db, str(run_id))
    return DeHaluPipeline(db).get_run(str(run_id))


@router.post('/runs/{run_id}/clarification', response_model=RunSummary, status_code=202)
def clarify(run_id: UUID, answers: ClarificationAnswers, db: Session = Depends(get_session)):
    require_run(db, run_id)
    try: resume(db, str(run_id), answers.answers, answers.language_hint)
    except ValueError as exc: raise HTTPException(409, str(exc)) from exc
    return DeHaluPipeline(db).get_run(str(run_id))


def poll(run_id, after):
    with SessionLocal() as db:
        events = db.scalars(select(RunEventRecord).where(RunEventRecord.run_id == run_id, RunEventRecord.sequence > after).order_by(RunEventRecord.sequence).limit(100)).all()
        run = db.get(RunRecord, run_id)
        return [e.payload for e in events], run.status if run else 'failed'


async def events(request: Request, run_id: UUID, after: int):
    terminal_polls = 0
    while not await request.is_disconnected():
        batch, status = await run_in_threadpool(poll, run_id, after)
        for event in batch:
            after = event['sequence']
            yield _sse(event)
        if status in TERMINAL and not batch:
            terminal_polls += 1
            if terminal_polls >= 3: return
        else: terminal_polls = 0
        yield ': heartbeat\n\n'
        await asyncio.sleep(.5)


def response_events(request, run_id, after):
    return StreamingResponse(events(request, run_id, after), media_type='text/event-stream', headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})


@router.get('/runs/{run_id}/events')
def stream_events(request: Request, run_id: UUID, after: int = Query(0, ge=0), last_event_id: str | None = Header(None), db: Session = Depends(get_session)):
    require_run(db, run_id)
    if last_event_id is not None:
        try:
            parsed = int(last_event_id)
            if parsed < 0: raise ValueError()
            after = max(after, parsed)
        except ValueError: raise HTTPException(400, 'Last-Event-ID must be a nonnegative event sequence')
    return response_events(request, run_id, after)


@router.post('/runs/stream')
def stream_run(request: Request, payload: RunCreate, db: Session = Depends(get_session)):
    run = enqueue(db, payload)
    return response_events(request, UUID(run.id), 0)


def _sse(event):
    return f"id: {event.get('sequence', '')}\ndata: {json.dumps(event)}\n\n"
