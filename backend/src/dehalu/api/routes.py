from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from dehalu.api.schemas import HealthResponse, RunCreate, RunEvidence, RunStreamCreate, RunSummary
from dehalu.core.settings import settings
from dehalu.services.pipeline import DeHaluPipeline
from dehalu.state.database import get_session


router = APIRouter(prefix="/api")


@router.get("/health", response_model=HealthResponse)
def health(db: Session = Depends(get_session)) -> HealthResponse:
    database_status = "ok"
    try:
        db.execute(text("select 1"))
    except Exception as exc:
        database_status = f"degraded: {exc}"
    judges = {
        "gemini": {"configured": bool(settings.gemini_api_key), "model": settings.gemini_model},
        "groq": {"configured": bool(settings.groq_api_key), "model": settings.groq_model},
        "mistral": {"configured": bool(settings.mistral_api_key), "model": settings.mistral_model},
    }
    ollama = {
        "base_url": settings.ollama_base_url,
        "model": settings.ollama_model,
        "fake_mode": settings.allow_fake_llm,
    }
    return HealthResponse(
        status="ok" if database_status == "ok" else "degraded",
        database=database_status,
        ollama=ollama,
        judges=judges,
    )


@router.post("/runs", response_model=RunSummary)
def create_run(request: RunCreate, db: Session = Depends(get_session)) -> RunSummary:
    try:
        return DeHaluPipeline(db).create_run(request)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/runs/stream")
def stream_run(request: RunStreamCreate, db: Session = Depends(get_session)) -> StreamingResponse:
    pipeline_request = RunCreate(
        prompt=request.prompt,
        language_hint=None,
        max_retry=settings.default_max_retry,
        constraints=request.constraints,
    )

    def events():
        try:
            for event in DeHaluPipeline(db).stream_run(pipeline_request):
                yield _sse(event)
        except Exception as exc:  # pragma: no cover - provider/database dependent
            yield _sse({"type": "error", "message": str(exc)})

    return StreamingResponse(events(), media_type="text/event-stream")


@router.get("/runs/{run_id}", response_model=RunSummary)
def get_run(run_id: str, db: Session = Depends(get_session)) -> RunSummary:
    result = DeHaluPipeline(db).get_run(run_id)
    if not result:
        raise HTTPException(status_code=404, detail="Run not found")
    return result


def _sse(event: dict) -> str:
    return f"data: {json.dumps(jsonable_encoder(event))}\n\n"


@router.get("/runs/{run_id}/evidence", response_model=RunEvidence)
def get_evidence(run_id: str, db: Session = Depends(get_session)) -> RunEvidence:
    result = DeHaluPipeline(db).get_evidence(run_id)
    if not result:
        raise HTTPException(status_code=404, detail="Run not found")
    return result
