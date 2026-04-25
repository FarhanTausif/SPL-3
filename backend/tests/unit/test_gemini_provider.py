from __future__ import annotations

import json

import httpx

from dehalu.adapters.llm import GeminiLLMProvider, build_provider_registry
from dehalu.core.settings import Settings
from dehalu.schemas import (
    CoderOutput,
    ExtractedClaim,
    JudgeResult,
    JudgeVerdict,
    NormalizedRequest,
    RiskLevel,
    SandboxResult,
    SandboxStatus,
)


def _settings(**overrides: object) -> Settings:
    return Settings(database_url="sqlite://", gemini_api_key="test-key", **overrides)


def _request() -> NormalizedRequest:
    return NormalizedRequest(
        prompt="Write Python code.",
        language="python",
        risk_level=RiskLevel.medium,
        latency_budget_seconds=15,
        provider="gemini",
    )


def _sandbox_result() -> SandboxResult:
    return SandboxResult(
        status=SandboxStatus.passed,
        check_type="compile_only",
        language="python",
        duration_ms=1.0,
    )


def _response_text(text: str) -> dict[str, object]:
    return {"candidates": [{"content": {"parts": [{"text": text}]}}]}


def test_build_provider_registry_only_adds_gemini_when_configured() -> None:
    disabled = build_provider_registry(Settings(database_url="sqlite://", gemini_api_key=None))
    enabled = build_provider_registry(_settings())

    assert disabled.health() == {"fake": True}
    assert enabled.health() == {"fake": True, "gemini": True}


def test_gemini_generate_judge_and_cove_parse_mocked_http() -> None:
    responses = iter(
        [
            httpx.Response(200, json=_response_text("```python\nprint('ok')\n```")),
            httpx.Response(
                200,
                json=_response_text(
                    json.dumps(
                        {
                            "verdict": "pass",
                            "hallucination_score": 0.1,
                            "findings": [],
                            "metrics": {"judge_mode": "structured"},
                        }
                    )
                ),
            ),
            httpx.Response(
                200,
                json=_response_text(
                    json.dumps(
                        {
                            "checks": [
                                {
                                    "claim": "print('ok')",
                                    "question": "Does the generated output print ok?",
                                    "answer": "Yes, the code prints ok.",
                                    "verdict": "supported",
                                    "metadata": {"kind": "code"},
                                }
                            ],
                            "findings": [],
                            "hallucination_score": 0.08,
                        }
                    )
                ),
            ),
        ]
    )
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return next(responses)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = GeminiLLMProvider(_settings(), http_client=client)
    request = _request()

    output = provider.generate(request)
    judge_result = provider.judge(request, output, [], [], _sandbox_result())
    cove_result = provider.cove(request, output, [], [], _sandbox_result(), judge_result)

    assert output.code == "print('ok')"
    assert judge_result.verdict == JudgeVerdict.pass_
    assert cove_result.verdict.value == "pass"
    assert cove_result.checks[0].claim == "print('ok')"
    assert requests[1].url.path.endswith(":generateContent")
    assert requests[1].headers["x-goog-api-key"] == "test-key"
    assert requests[1].read().decode()


def test_gemini_judge_turns_malformed_json_into_warning_finding() -> None:
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json=_response_text("{not-json"))
        )
    )
    provider = GeminiLLMProvider(_settings(), http_client=client)
    request = _request()
    output = CoderOutput(provider="gemini", model="gemini-2.0-flash", language="python", code="print('ok')\n")

    result = provider.judge(request, output, [], [], _sandbox_result())

    assert result.verdict == JudgeVerdict.uncertain
    assert any(finding.code == "judge_provider_error" for finding in result.findings)


def test_gemini_cove_turns_malformed_json_into_warning_finding() -> None:
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json=_response_text("{not-json"))
        )
    )
    provider = GeminiLLMProvider(_settings(), http_client=client)
    request = _request()
    output = CoderOutput(provider="gemini", model="gemini-2.0-flash", language="python", code="print('ok')\n")
    judge_result = JudgeResult(
        verdict=JudgeVerdict.pass_,
        provider="gemini",
        model="gemini-2.0-flash",
        duration_ms=1.0,
        hallucination_score=0.05,
    )
    claims = [ExtractedClaim(kind="code", value="print('ok')", source="code")]

    result = provider.cove(request, output, claims, [], _sandbox_result(), judge_result)

    assert result.verdict.value == "uncertain"
    assert any(finding.code == "cove_provider_error" for finding in result.findings)
