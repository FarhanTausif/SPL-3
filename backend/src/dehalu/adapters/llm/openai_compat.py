from __future__ import annotations

from time import perf_counter
from typing import Any

import httpx
from pydantic import BaseModel, Field, ValidationError

from dehalu.adapters.llm.runtime import (
    ProviderExecutionError,
    build_invocation_record,
    classify_provider_failure,
)
from dehalu.orchestration.prompts import (
    PromptRender,
    clarification_prompt,
    cove_prompt,
    generation_prompt,
    judge_prompt,
    repair_prompt,
)
from dehalu.schemas import (
    AgentRole,
    ClarificationResult,
    CoderOutput,
    CoVeClaimCheck,
    CoVeFinding,
    CoVeResult,
    ExtractedClaim,
    JudgeFinding,
    JudgeResult,
    JudgeVerdict,
    NormalizedRequest,
    PolicyDecision,
    ProviderFailureKind,
    SandboxResult,
    StaticFinding,
    StaticFindingSeverity,
)
from dehalu.verification.judges import build_cove_result


class _JudgePayload(BaseModel):
    verdict: JudgeVerdict
    hallucination_score: float = Field(ge=0.0, le=1.0)
    findings: list[JudgeFinding] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)


class _CoVePayload(BaseModel):
    checks: list[CoVeClaimCheck] = Field(default_factory=list)
    findings: list[CoVeFinding] = Field(default_factory=list)
    hallucination_score: float | None = Field(default=None, ge=0.0, le=1.0)


class _ClarificationPayload(BaseModel):
    requested_outcome: str
    language: str
    runtime_assumptions: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)
    ambiguity_flags: list[str] = Field(default_factory=list)
    needs_user_input: bool = False
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class OpenAICompatibleLLMProvider:
    def __init__(
        self,
        *,
        name: str,
        api_key: str | None,
        base_url: str,
        generate_model: str,
        verify_model: str,
        timeout_seconds: float,
        http_client: httpx.Client | None = None,
        retry_attempts: int = 1,
        prompt_policy_version: str = "v1",
        routing_policy_version: str = "v1",
        capture_full_payloads: bool = False,
        smoke_checks_enabled: bool = False,
    ) -> None:
        self.name = name
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.generate_model = generate_model
        self.verify_model = verify_model
        self.timeout_seconds = timeout_seconds
        self.retry_attempts = retry_attempts
        self.prompt_policy_version = prompt_policy_version
        self.routing_policy_version = routing_policy_version
        self.capture_full_payloads = capture_full_payloads
        self.smoke_checks_enabled = smoke_checks_enabled
        self._client = http_client or httpx.Client(timeout=self.timeout_seconds)

    def clarify(self, request: NormalizedRequest) -> ClarificationResult:
        render = clarification_prompt(self.name, request)
        try:
            text, invocation = self._chat_completion(
                model=self.verify_model,
                render=render,
                role=AgentRole.clarifier,
                response_format={"type": "json_object"},
            )
            payload = _ClarificationPayload.model_validate_json(text)
            clarified_prompt = request.prompt.strip()
            if payload.constraints:
                clarified_prompt = f"{clarified_prompt}\nConstraints: {'; '.join(payload.constraints)}"
            return ClarificationResult(
                clarified_prompt=clarified_prompt,
                requested_outcome=payload.requested_outcome,
                language=payload.language or request.language,
                runtime_assumptions=payload.runtime_assumptions,
                constraints=payload.constraints,
                acceptance_criteria=payload.acceptance_criteria or request.acceptance_criteria,
                ambiguity_flags=payload.ambiguity_flags,
                needs_user_input=payload.needs_user_input,
                confidence=payload.confidence,
                metadata=self._metadata(invocation),
            )
        except ProviderExecutionError as exc:
            return self._clarification_fallback(request, exc.record)
        except (ValidationError, ValueError) as exc:
            failure_kind, _ = classify_provider_failure(exc)
            record = build_invocation_record(
                provider_name=self.name,
                model=self.verify_model,
                stage="clarification",
                role=AgentRole.clarifier,
                started_at=perf_counter(),
                retry_count=0,
                prompt_template_version=render.version,
                routing_policy_version=self.routing_policy_version,
                success=False,
                failure_kind=failure_kind,
                metadata={"error_type": type(exc).__name__, "parse_failure": True},
            )
            return self._clarification_fallback(request, record)

    def generate(self, request: NormalizedRequest) -> CoderOutput:
        render = generation_prompt(self.name, request)
        text, invocation = self._chat_completion(
            model=self.generate_model,
            render=render,
            role=AgentRole.coder,
        )
        return CoderOutput(
            provider=self.name,
            model=self.generate_model,
            language=request.language,
            code=self._strip_code_fences(text),
            assumptions=[
                f"Generated by {self.name} through the backend provider adapter.",
                f"Language selected as {request.language}.",
            ],
            dependencies=[],
            files_touched=[],
            execution_notes=["No runtime execution was performed in this iteration."],
            metadata=self._metadata(invocation),
        )

    def judge(
        self,
        request: NormalizedRequest,
        output: CoderOutput,
        claims: list[ExtractedClaim],
        static_findings: list[StaticFinding],
        sandbox_result: SandboxResult,
    ) -> JudgeResult:
        started_at = perf_counter()
        render = judge_prompt(self.name, request, output, claims, static_findings, sandbox_result)
        try:
            text, invocation = self._chat_completion(
                model=self.verify_model,
                render=render,
                role=AgentRole.judge,
                response_format={"type": "json_object"},
            )
            payload = _JudgePayload.model_validate_json(text)
            return JudgeResult(
                verdict=payload.verdict,
                provider=self.name,
                model=self.verify_model,
                duration_ms=round((perf_counter() - started_at) * 1000, 3),
                hallucination_score=payload.hallucination_score,
                findings=payload.findings,
                metrics={
                    **payload.metrics,
                    "claim_count": len(claims),
                    "static_finding_count": len(static_findings),
                    "sandbox_status": sandbox_result.status.value,
                    "provider_invocation": invocation.model_dump(mode="json"),
                },
            )
        except ProviderExecutionError as exc:
            return self._judge_fallback(started_at, claims, static_findings, sandbox_result, exc.record, exc)
        except (ValidationError, ValueError) as exc:
            failure_kind, _ = classify_provider_failure(exc)
            record = build_invocation_record(
                provider_name=self.name,
                model=self.verify_model,
                stage="judge",
                role=AgentRole.judge,
                started_at=started_at,
                retry_count=0,
                prompt_template_version=render.version,
                routing_policy_version=self.routing_policy_version,
                success=False,
                failure_kind=failure_kind,
                metadata={"error_type": type(exc).__name__, "parse_failure": True},
            )
            return self._judge_fallback(started_at, claims, static_findings, sandbox_result, record, exc)

    def cove(
        self,
        request: NormalizedRequest,
        output: CoderOutput,
        claims: list[ExtractedClaim],
        static_findings: list[StaticFinding],
        sandbox_result: SandboxResult,
        judge_result: JudgeResult,
    ) -> CoVeResult:
        started_at = perf_counter()
        render = cove_prompt(self.name, request, output, claims, static_findings, sandbox_result, judge_result)
        try:
            text, invocation = self._chat_completion(
                model=self.verify_model,
                render=render,
                role=AgentRole.cove,
                response_format={"type": "json_object"},
            )
            payload = _CoVePayload.model_validate_json(text)
            result = build_cove_result(
                provider=self.name,
                model=self.verify_model,
                duration_ms=(perf_counter() - started_at) * 1000,
                checks=payload.checks,
                extra_findings=payload.findings,
                hallucination_score=payload.hallucination_score,
            )
            result.metrics.update(
                {
                    "claim_count": len(claims),
                    "static_finding_count": len(static_findings),
                    "sandbox_status": sandbox_result.status.value,
                    "judge_verdict": judge_result.verdict.value,
                    "provider_invocation": invocation.model_dump(mode="json"),
                }
            )
            return result
        except ProviderExecutionError as exc:
            return self._cove_fallback(started_at, claims, static_findings, sandbox_result, judge_result, exc.record, exc)
        except (ValidationError, ValueError) as exc:
            failure_kind, _ = classify_provider_failure(exc)
            record = build_invocation_record(
                provider_name=self.name,
                model=self.verify_model,
                stage="cove",
                role=AgentRole.cove,
                started_at=started_at,
                retry_count=0,
                prompt_template_version=render.version,
                routing_policy_version=self.routing_policy_version,
                success=False,
                failure_kind=failure_kind,
                metadata={"error_type": type(exc).__name__, "parse_failure": True},
            )
            return self._cove_fallback(started_at, claims, static_findings, sandbox_result, judge_result, record, exc)

    def repair(
        self,
        request: NormalizedRequest,
        output: CoderOutput,
        policy_decision: PolicyDecision,
        judge_result: JudgeResult,
        cove_result: CoVeResult,
    ) -> CoderOutput:
        render = repair_prompt(self.name, request, output, policy_decision, judge_result, cove_result)
        try:
            text, invocation = self._chat_completion(
                model=self.verify_model,
                render=render,
                role=AgentRole.repair,
            )
            cleaned = self._strip_code_fences(text)
            if not cleaned.strip():
                raise ValueError(f"{self.name} repair output was empty.")
            return CoderOutput(
                provider=self.name,
                model=self.verify_model,
                language=request.language,
                code=cleaned,
                assumptions=[
                    f"Generated by {self.name} repair flow through the backend provider adapter.",
                    f"Language selected as {request.language}.",
                ],
                dependencies=[],
                files_touched=[],
                execution_notes=[f"{self.name} repair returned revised code for re-verification."],
                metadata=self._metadata(invocation),
            )
        except ProviderExecutionError as exc:
            return self._repair_fallback(request, exc.record, f"{self.name} repair failed: {exc}")
        except ValueError as exc:
            failure_kind, _ = classify_provider_failure(exc)
            record = build_invocation_record(
                provider_name=self.name,
                model=self.verify_model,
                stage="repair",
                role=AgentRole.repair,
                started_at=perf_counter(),
                retry_count=0,
                prompt_template_version=render.version,
                routing_policy_version=self.routing_policy_version,
                success=False,
                failure_kind=failure_kind,
                metadata={"error_type": type(exc).__name__},
            )
            return self._repair_fallback(request, record, f"{self.name} repair failed: {exc}")

    def healthcheck(self) -> bool:
        return bool(self.api_key)

    def health_details(self) -> dict[str, Any]:
        live_status = "skipped"
        if self.smoke_checks_enabled and self.api_key:
            try:
                self._chat_completion(
                    model=self.verify_model,
                    render=PromptRender(
                        system_instruction="Reply with OK.",
                        prompt="OK",
                        version=self.prompt_policy_version,
                        role="smokecheck",
                        provider_name=self.name,
                    ),
                    role=AgentRole.judge,
                )
                live_status = "passed"
            except Exception:
                live_status = "failed"
        return {
            "configured": bool(self.api_key),
            "api_key_present": bool(self.api_key),
            "smoke_check_enabled": self.smoke_checks_enabled,
            "live_smoke_check": live_status,
            "models": {
                "generate": self.generate_model,
                "verify": self.verify_model,
            },
            "retry_attempts": self.retry_attempts,
        }

    def _chat_completion(
        self,
        *,
        model: str,
        render: PromptRender,
        role: AgentRole,
        response_format: dict[str, Any] | None = None,
    ) -> tuple[str, Any]:
        if not self.api_key:
            record = build_invocation_record(
                provider_name=self.name,
                model=model,
                stage=render.role,
                role=role,
                started_at=perf_counter(),
                retry_count=0,
                prompt_template_version=render.version,
                routing_policy_version=self.routing_policy_version,
                success=False,
                failure_kind=ProviderFailureKind.misconfiguration,
                request_summary={"response_format": response_format or {}, "model": model},
                metadata={"error_type": "MissingAPIKey"},
            )
            raise ProviderExecutionError(f"{self.name} provider is not configured.", record=record)

        started_at = perf_counter()
        retry_count = 0
        while True:
            try:
                payload: dict[str, Any] = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": render.system_instruction},
                        {"role": "user", "content": render.prompt},
                    ],
                    "temperature": 0.0,
                }
                if response_format:
                    payload["response_format"] = response_format
                response = self._client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    json=payload,
                )
                response.raise_for_status()
                body = response.json()
                choices = body.get("choices", [])
                if not choices:
                    raise ValueError(f"{self.name} response did not contain choices.")
                content = choices[0].get("message", {}).get("content", "")
                if not content:
                    raise ValueError(f"{self.name} response did not contain message content.")
                record = build_invocation_record(
                    provider_name=self.name,
                    model=model,
                    stage=render.role,
                    role=role,
                    started_at=started_at,
                    retry_count=retry_count,
                    prompt_template_version=render.version,
                    routing_policy_version=self.routing_policy_version,
                    success=True,
                    usage=body.get("usage", {}),
                    request_summary=self._request_summary(model, render, response_format),
                    response_summary=self._response_summary(body, content),
                    metadata={"http_status": response.status_code},
                )
                return content.strip(), record
            except Exception as exc:
                failure_kind, retryable = classify_provider_failure(exc if isinstance(exc, Exception) else Exception())
                if retryable and retry_count < self.retry_attempts:
                    retry_count += 1
                    continue
                record = build_invocation_record(
                    provider_name=self.name,
                    model=model,
                    stage=render.role,
                    role=role,
                    started_at=started_at,
                    retry_count=retry_count,
                    prompt_template_version=render.version,
                    routing_policy_version=self.routing_policy_version,
                    success=False,
                    failure_kind=failure_kind,
                    request_summary=self._request_summary(model, render, response_format),
                    response_summary={},
                    metadata={"error_type": type(exc).__name__, "message": str(exc)},
                )
                raise ProviderExecutionError(str(exc), record=record) from exc

    def _metadata(self, invocation) -> dict[str, Any]:
        return {
            "provider": self.name,
            "prompt_template_version": invocation.prompt_template_version,
            "routing_policy_version": invocation.routing_policy_version,
            "provider_invocation": invocation.model_dump(mode="json"),
        }

    def _clarification_fallback(self, request: NormalizedRequest, invocation) -> ClarificationResult:
        return ClarificationResult(
            clarified_prompt=request.prompt,
            requested_outcome=request.prompt,
            language=request.language,
            runtime_assumptions=[],
            constraints=[],
            acceptance_criteria=request.acceptance_criteria,
            ambiguity_flags=[],
            needs_user_input=False,
            confidence=0.35,
            metadata={
                "provider": self.name,
                "model": self.verify_model,
                "fallback": True,
                "provider_invocation": invocation.model_dump(mode="json"),
            },
        )

    def _judge_fallback(self, started_at, claims, static_findings, sandbox_result, invocation, exc: Exception) -> JudgeResult:
        return JudgeResult(
            verdict=JudgeVerdict.uncertain,
            provider=self.name,
            model=self.verify_model,
            duration_ms=round((perf_counter() - started_at) * 1000, 3),
            hallucination_score=0.6,
            findings=[
                JudgeFinding(
                    code="judge_provider_error",
                    message=f"{self.name} judge output could not be validated: {exc}",
                    severity=StaticFindingSeverity.warning,
                    metadata={"error_type": type(exc).__name__},
                )
            ],
            metrics={
                "claim_count": len(claims),
                "static_finding_count": len(static_findings),
                "sandbox_status": sandbox_result.status.value,
                "provider_error": type(exc).__name__,
                "provider_invocation": invocation.model_dump(mode="json"),
            },
        )

    def _cove_fallback(self, started_at, claims, static_findings, sandbox_result, judge_result, invocation, exc: Exception) -> CoVeResult:
        result = build_cove_result(
            provider=self.name,
            model=self.verify_model,
            duration_ms=(perf_counter() - started_at) * 1000,
            checks=[],
            extra_findings=[
                CoVeFinding(
                    code="cove_provider_error",
                    message=f"{self.name} CoVe output could not be validated: {exc}",
                    severity=StaticFindingSeverity.warning,
                    metadata={"error_type": type(exc).__name__},
                )
            ],
            hallucination_score=0.6,
        )
        result.metrics.update(
            {
                "claim_count": len(claims),
                "static_finding_count": len(static_findings),
                "sandbox_status": sandbox_result.status.value,
                "judge_verdict": judge_result.verdict.value,
                "provider_error": type(exc).__name__,
                "provider_invocation": invocation.model_dump(mode="json"),
            }
        )
        return result

    def _repair_fallback(self, request: NormalizedRequest, invocation, note: str) -> CoderOutput:
        return CoderOutput(
            provider=self.name,
            model=self.verify_model,
            language=request.language,
            code="",
            assumptions=[
                f"{self.name} repair did not return a valid replacement output.",
                f"Language selected as {request.language}.",
            ],
            dependencies=[],
            files_touched=[],
            execution_notes=[note],
            metadata=self._metadata(invocation),
        )

    def _request_summary(self, model: str, render: PromptRender, response_format: dict[str, Any] | None) -> dict[str, Any]:
        return {
            "model": model,
            "prompt_length": len(render.prompt),
            "system_length": len(render.system_instruction),
            "response_format": response_format or {},
        }

    def _response_summary(self, body: dict[str, Any], content: str) -> dict[str, Any]:
        summary = {
            "choice_count": len(body.get("choices", [])),
            "text_length": len(content),
        }
        if body.get("usage"):
            summary["usage"] = body["usage"]
        if self.capture_full_payloads:
            summary["raw_response"] = body
        return summary

    def _strip_code_fences(self, text: str) -> str:
        stripped = text.strip()
        if not stripped.startswith("```"):
            return stripped
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        return "\n".join(lines).strip()
