from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from dehalu.agents.compat import HAS_CREWAI
from dehalu.adapters.llm.registry import UnknownProviderError
from dehalu.api.dependencies import (
    get_app_settings,
    get_orchestrator,
    get_provider_registry,
)
from dehalu.core.settings import Settings
from dehalu.orchestration import RunOrchestrator
from dehalu.schemas import HealthResponse, RunDetail, RunEvent, RunRequest, RunResponse, VerificationEvidence
from dehalu.state.database import get_session
from dehalu.state.repository import RunNotFoundError, RunRepository

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health(
    settings: Settings = Depends(get_app_settings),
    providers=Depends(get_provider_registry),
    orchestrator: RunOrchestrator = Depends(get_orchestrator),
    session: Session = Depends(get_session),
) -> HealthResponse:
    provider_health = providers.health()
    provider_details = providers.health_details() if hasattr(providers, "health_details") else {}
    status_value = "ok" if all(provider_health.values()) else "degraded"
    repository = RunRepository(session)
    return HealthResponse(
        status=status_value,
        version=settings.app_version,
        providers=provider_health,
        orchestration={
            "configured_mode": settings.orchestration_mode,
            "crewai_available": HAS_CREWAI,
            "crewai_enabled": settings.orchestration_mode == "crewai" and HAS_CREWAI,
            "advanced_run_mode": "worker_backed",
            "worker_id": settings.worker_id,
            "worker_freshness": repository.worker_freshness(
                settings.worker_id,
                stale_after_seconds=settings.worker_lease_seconds * 2,
            ),
            "queue_backlog": repository.queue_backlog_summary(),
            "provider_role_readiness": orchestrator.router.readiness(),
            "routing_policy_version": settings.routing_policy_version,
            "prompt_policy_version": settings.prompt_policy_version,
            "provider_health_details": provider_details,
        },
    )


@router.post("/v1/runs", response_model=RunResponse, status_code=status.HTTP_201_CREATED)
async def create_run(
    request: RunRequest,
    session: Session = Depends(get_session),
    orchestrator: RunOrchestrator = Depends(get_orchestrator),
) -> RunResponse:
    try:
        return orchestrator.run(request, session)
    except UnknownProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown provider: {exc}",
        ) from exc


@router.get("/v1/runs/{run_id}", response_model=RunDetail)
async def get_run(
    run_id: str,
    session: Session = Depends(get_session),
    orchestrator: RunOrchestrator = Depends(get_orchestrator),
) -> RunDetail:
    try:
        return orchestrator.get_run_detail(run_id, session)
    except RunNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found") from exc


@router.get("/v1/runs/{run_id}/evidence", response_model=list[VerificationEvidence])
async def get_evidence(
    run_id: str,
    session: Session = Depends(get_session),
) -> list[VerificationEvidence]:
    repository = RunRepository(session)
    try:
        return repository.get_run_evidence(run_id)
    except RunNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found") from exc


@router.get("/v1/runs/{run_id}/events", response_model=list[RunEvent])
async def get_run_events(
    run_id: str,
    session: Session = Depends(get_session),
    orchestrator: RunOrchestrator = Depends(get_orchestrator),
) -> list[RunEvent]:
    try:
        return orchestrator.get_run_events(run_id, session)
    except RunNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found") from exc
