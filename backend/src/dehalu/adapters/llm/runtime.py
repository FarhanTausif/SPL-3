from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any

import httpx

from dehalu.schemas import AgentRole, ProviderFailureKind, ProviderInvocationRecord


@dataclass(slots=True)
class InvocationOutcome:
    record: ProviderInvocationRecord
    response_body: dict[str, Any] | None = None
    text: str | None = None


class ProviderExecutionError(RuntimeError):
    def __init__(self, message: str, *, record: ProviderInvocationRecord) -> None:
        super().__init__(message)
        self.record = record


def classify_provider_failure(exc: Exception) -> tuple[ProviderFailureKind, bool]:
    if isinstance(exc, ValueError):
        lowered = str(exc).lower()
        if "configured" in lowered or "api key" in lowered:
            return ProviderFailureKind.misconfiguration, False
        if "empty" in lowered:
            return ProviderFailureKind.empty_output, False
        return ProviderFailureKind.malformed_output, False
    if isinstance(exc, httpx.HTTPStatusError):
        status_code = exc.response.status_code
        if status_code == 429:
            return ProviderFailureKind.rate_limited, True
        if status_code in {401, 403}:
            return ProviderFailureKind.auth, False
        if status_code >= 500:
            return ProviderFailureKind.transient_http, True
        return ProviderFailureKind.unknown, False
    if isinstance(exc, httpx.TimeoutException):
        return ProviderFailureKind.transport, True
    if isinstance(exc, httpx.HTTPError):
        return ProviderFailureKind.transport, True
    return ProviderFailureKind.unknown, False


def build_invocation_record(
    *,
    provider_name: str,
    model: str,
    stage: str,
    role: AgentRole,
    started_at: float,
    retry_count: int,
    prompt_template_version: str,
    routing_policy_version: str,
    success: bool,
    failure_kind: ProviderFailureKind = ProviderFailureKind.none,
    fallback_used: bool = False,
    usage: dict[str, Any] | None = None,
    request_summary: dict[str, Any] | None = None,
    response_summary: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> ProviderInvocationRecord:
    return ProviderInvocationRecord(
        provider_name=provider_name,
        model=model,
        stage=stage,
        role=role,
        success=success,
        latency_ms=round((perf_counter() - started_at) * 1000, 3),
        retry_count=retry_count,
        fallback_used=fallback_used,
        failure_kind=failure_kind,
        prompt_template_version=prompt_template_version,
        routing_policy_version=routing_policy_version,
        usage=usage or {},
        request_summary=request_summary or {},
        response_summary=response_summary or {},
        metadata=metadata or {},
    )
