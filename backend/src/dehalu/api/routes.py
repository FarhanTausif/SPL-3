from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from dehalu.agents.compat import HAS_CREWAI
from dehalu.adapters.llm.registry import UnknownProviderError
from dehalu.api.dependencies import (
    get_app_settings,
    get_orchestrator,
    get_provider_registry,
)
from dehalu.core.settings import Settings
from dehalu.orchestration.service import RequestedProviderUnavailableError
from dehalu.orchestration import RunOrchestrator
from dehalu.schemas import HealthResponse, RunDetail, RunEvent, RunRequest, RunResponse, VerificationEvidence
from dehalu.state.database import get_session
from dehalu.state.repository import RunNotFoundError, RunRepository

router = APIRouter()


def _build_health_response(
    *,
    settings: Settings,
    providers,
    orchestrator: RunOrchestrator,
    session: Session,
) -> HealthResponse:
    provider_health = providers.health()
    provider_details = providers.health_details() if hasattr(providers, "health_details") else {}
    normalized_provider_details = _normalize_provider_health_details(provider_health, provider_details)
    status_value = "ok" if all(provider_health.values()) else "degraded"
    repository = RunRepository(session)
    queue_backlog = repository.queue_backlog_summary()
    worker_freshness = repository.worker_freshness(
        settings.worker_id,
        stale_after_seconds=settings.worker_lease_seconds * 2,
    )
    provider_role_readiness = orchestrator.router.readiness()
    worker_readiness = _summarize_worker_readiness(worker_freshness, queue_backlog)
    live_providers = [name for name in provider_health if name != "fake"]
    healthy_live_providers = [name for name in live_providers if provider_health.get(name)]
    live_provider_operation_ready = bool(healthy_live_providers) and bool(
        provider_role_readiness.get("live_provider_operation_ready")
    )
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
            "worker_freshness": worker_freshness,
            "queue_backlog": queue_backlog,
            "worker_readiness": worker_readiness,
            "provider_role_readiness": provider_role_readiness,
            "routing_policy_version": settings.routing_policy_version,
            "prompt_policy_version": settings.prompt_policy_version,
            "provider_health_details": normalized_provider_details,
            "live_provider_readiness": {
                "configured_live_providers": live_providers,
                "healthy_live_providers": healthy_live_providers,
                "live_provider_operation_ready": live_provider_operation_ready,
            },
        },
    )


def _normalize_provider_health_details(
    provider_health: dict[str, bool],
    provider_details: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    normalized: dict[str, dict[str, Any]] = {}
    for provider_name, healthy in provider_health.items():
        details = provider_details.get(provider_name, {})
        configured = bool(details.get("configured", healthy))
        smoke_status = details.get("live_smoke_check", "unknown")
        normalized[provider_name] = {
            "configured": configured,
            "api_key_present": bool(details.get("api_key_present", configured)),
            "smoke_check_enabled": bool(details.get("smoke_check_enabled", False)),
            "live_smoke_check": smoke_status,
            "models": details.get("models", {}),
            "retry_attempts": int(details.get("retry_attempts", 0)),
            "healthy": healthy,
            "ready_for_live_routing": healthy and smoke_status in {"passed", "skipped"},
        }
    return normalized


def _summarize_worker_readiness(
    worker_freshness: dict[str, Any],
    queue_backlog: dict[str, int],
) -> dict[str, Any]:
    total_backlog = int(queue_backlog.get("total", queue_backlog.get("queued", 0) + queue_backlog.get("running", 0)))
    has_heartbeat = bool(worker_freshness.get("last_heartbeat_at"))
    is_fresh = bool(worker_freshness.get("fresh"))
    if not has_heartbeat and total_backlog == 0:
        state = "idle"
        ready = True
    elif not has_heartbeat:
        state = "missing"
        ready = False
    elif is_fresh:
        state = "fresh"
        ready = True
    else:
        state = "stale"
        ready = total_backlog == 0
    return {"state": state, "ready": ready, "backlog_aware": total_backlog > 0}


@router.get("/health", response_model=HealthResponse)
async def health(
    settings: Settings = Depends(get_app_settings),
    providers=Depends(get_provider_registry),
    orchestrator: RunOrchestrator = Depends(get_orchestrator),
    session: Session = Depends(get_session),
) -> HealthResponse:
    return _build_health_response(
        settings=settings,
        providers=providers,
        orchestrator=orchestrator,
        session=session,
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
            detail=f"Unknown provider '{exc}'.",
        ) from exc
    except RequestedProviderUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
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


@router.websocket("/v1/runs/{run_id}/stream")
async def stream_run(
    websocket: WebSocket,
    run_id: str,
    settings: Settings = Depends(get_app_settings),
    providers=Depends(get_provider_registry),
    orchestrator: RunOrchestrator = Depends(get_orchestrator),
    session: Session = Depends(get_session),
) -> None:
    await websocket.accept()
    repository = RunRepository(session)
    last_status: str | None = None
    last_stage_signature: tuple[tuple[str, str], ...] = ()
    last_evidence_count = -1
    last_event_count = -1

    async def send_envelope(message_type: str, data: dict[str, Any]) -> None:
        await websocket.send_json(
            jsonable_encoder(
                {
                    "type": message_type,
                    "runId": run_id,
                    "timestamp": int(asyncio.get_running_loop().time() * 1000),
                    "data": data,
                }
            )
        )

    try:
        while True:
            session.expire_all()
            try:
                run = orchestrator.get_run_detail(run_id, session)
                evidence = repository.get_run_evidence(run_id)
                events = repository.get_run_events(run_id)
            except RunNotFoundError:
                await send_envelope("error", {"message": "Run not found"})
                await websocket.close(code=1008)
                return

            snapshot = {
                "run": run.model_dump(mode="json"),
                "evidence": [item.model_dump(mode="json") for item in evidence],
                "events": [item.model_dump(mode="json") for item in events],
                "health": _build_health_response(
                    settings=settings,
                    providers=providers,
                    orchestrator=orchestrator,
                    session=session,
                ).model_dump(mode="json"),
            }

            if last_status is None:
                await send_envelope("run.snapshot", snapshot)
            elif run.status.value != last_status:
                await send_envelope(
                    "run.updated",
                    {
                        "status": run.status.value,
                        "stage": run.stage_summary[-1].stage if run.stage_summary else "lifecycle",
                    },
                )

            stage_signature = tuple((stage.stage, stage.status) for stage in run.stage_summary)
            if last_stage_signature and stage_signature != last_stage_signature and run.stage_summary:
                await send_envelope(
                    "stage.updated",
                    {
                        "run": run.model_dump(mode="json"),
                        "stage": run.stage_summary[-1].model_dump(mode="json"),
                    },
                )

            if last_evidence_count >= 0 and len(evidence) != last_evidence_count:
                await send_envelope(
                    "evidence.collected",
                    {
                        "evidence": [item.model_dump(mode="json") for item in evidence],
                        "events": [item.model_dump(mode="json") for item in events],
                    },
                )

            terminal = run.status.value in {"completed", "failed", "needs_clarification"}
            if terminal:
                await send_envelope(
                    "run.failed" if run.status.value == "failed" else "run.completed",
                    snapshot,
                )
                await websocket.close(code=1000)
                return

            last_status = run.status.value
            last_stage_signature = stage_signature
            last_evidence_count = len(evidence)
            last_event_count = len(events)

            await send_envelope("ping", {"event_count": last_event_count})
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        return
