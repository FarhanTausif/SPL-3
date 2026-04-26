from __future__ import annotations

import json
from time import perf_counter
from typing import Any

import httpx
from pydantic import BaseModel, Field, ValidationError

from dehalu.schemas import (
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
    ) -> None:
        self.name = name
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.generate_model = generate_model
        self.verify_model = verify_model
        self.timeout_seconds = timeout_seconds
        self._client = http_client or httpx.Client(timeout=self.timeout_seconds)

    def clarify(self, request: NormalizedRequest) -> ClarificationResult:
        try:
            text = self._chat_completion(
                model=self.verify_model,
                system_instruction=(
                    "You clarify software requests before generation. "
                    "Return strict JSON only."
                ),
                prompt=(
                    "Normalize the coding request into a structured task spec.\n"
                    f"Request:\n{request.model_dump_json(indent=2)}\n"
                ),
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
                metadata={"provider": self.name, "model": self.verify_model},
            )
        except (ValidationError, ValueError, httpx.HTTPError):
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
                metadata={"provider": self.name, "model": self.verify_model, "fallback": True},
            )

    def generate(self, request: NormalizedRequest) -> CoderOutput:
        code = self._chat_completion(
            model=self.generate_model,
            system_instruction=(
                "You are a coding model inside a verification gateway. "
                "Return only source code without markdown fences."
            ),
            prompt=(
                "Return only source code.\n"
                f"Requested language: {request.language}\n"
                f"Risk level: {request.risk_level.value}\n"
                f"Latency budget seconds: {request.latency_budget_seconds}\n"
                f"Framework hint: {request.framework_hint or 'none'}\n"
                f"User prompt:\n{request.prompt}\n"
            ),
        )
        return CoderOutput(
            provider=self.name,
            model=self.generate_model,
            language=request.language,
            code=self._strip_code_fences(code),
            assumptions=[
                f"Generated by {self.name} through the synchronous backend provider adapter.",
                f"Language selected as {request.language}.",
            ],
            dependencies=[],
            files_touched=[],
            execution_notes=["No runtime execution was performed in this iteration."],
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
        try:
            text = self._chat_completion(
                model=self.verify_model,
                system_instruction="You are a code hallucination judge. Return strict JSON only.",
                prompt=(
                    "Evaluate whether the generated code is hallucinated or unsupported.\n"
                    "Use only the evidence below.\n\n"
                    f"Normalized request:\n{request.model_dump_json(indent=2)}\n\n"
                    f"Coder output:\n{output.model_dump_json(indent=2)}\n\n"
                    f"Extracted claims:\n{self._dump_models(claims)}\n\n"
                    f"Static findings:\n{self._dump_models(static_findings)}\n\n"
                    f"Sandbox result:\n{sandbox_result.model_dump_json(indent=2)}\n"
                ),
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
                },
            )
        except (ValidationError, ValueError, httpx.HTTPError) as exc:
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
                },
            )

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
        try:
            text = self._chat_completion(
                model=self.verify_model,
                system_instruction="You are a Chain-of-Verification checker for generated code. Return strict JSON only.",
                prompt=(
                    "Re-check each extracted claim independently against the generated code.\n"
                    "Return one structured check per claim and summarize unsupported or uncertain claims.\n\n"
                    f"Normalized request:\n{request.model_dump_json(indent=2)}\n\n"
                    f"Coder output:\n{output.model_dump_json(indent=2)}\n\n"
                    f"Extracted claims:\n{self._dump_models(claims)}\n\n"
                    f"Static findings:\n{self._dump_models(static_findings)}\n\n"
                    f"Sandbox result:\n{sandbox_result.model_dump_json(indent=2)}\n\n"
                    f"Judge result:\n{judge_result.model_dump_json(indent=2)}\n"
                ),
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
                }
            )
            return result
        except (ValidationError, ValueError, httpx.HTTPError) as exc:
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
                }
            )
            return result

    def repair(
        self,
        request: NormalizedRequest,
        output: CoderOutput,
        policy_decision: PolicyDecision,
        judge_result: JudgeResult,
        cove_result: CoVeResult,
    ) -> CoderOutput:
        try:
            code = self._chat_completion(
                model=self.verify_model,
                system_instruction=(
                    "You repair generated source code after hallucination detection. "
                    "Return only revised source code without markdown fences."
                ),
                prompt=(
                    "Revise the generated code to address hallucination or unsupported-claim findings.\n"
                    "Return only corrected source code.\n\n"
                    f"Normalized request:\n{request.model_dump_json(indent=2)}\n\n"
                    f"Current coder output:\n{output.model_dump_json(indent=2)}\n\n"
                    f"Policy decision:\n{policy_decision.model_dump_json(indent=2)}\n\n"
                    f"Judge result:\n{judge_result.model_dump_json(indent=2)}\n\n"
                    f"CoVe result:\n{cove_result.model_dump_json(indent=2)}\n"
                ),
            )
            cleaned = self._strip_code_fences(code)
            if not cleaned.strip():
                raise ValueError(f"{self.name} repair output was empty.")
            return CoderOutput(
                provider=self.name,
                model=self.verify_model,
                language=request.language,
                code=cleaned,
                assumptions=[
                    f"Generated by {self.name} repair flow through the synchronous backend provider adapter.",
                    f"Language selected as {request.language}.",
                ],
                dependencies=[],
                files_touched=[],
                execution_notes=[f"{self.name} repair returned revised code for re-verification."],
            )
        except (ValueError, httpx.HTTPError) as exc:
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
                execution_notes=[f"{self.name} repair failed: {exc}"],
            )

    def healthcheck(self) -> bool:
        return bool(self.api_key)

    def _chat_completion(
        self,
        *,
        model: str,
        system_instruction: str,
        prompt: str,
        response_format: dict[str, Any] | None = None,
    ) -> str:
        if not self.api_key:
            raise ValueError(f"{self.name} provider is not configured.")

        payload: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt},
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
        return content.strip()

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

    def _dump_models(self, models: list[BaseModel]) -> str:
        if not models:
            return "[]"
        return "[\n" + ",\n".join(model.model_dump_json(indent=2) for model in models) + "\n]"
