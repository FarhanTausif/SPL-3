from __future__ import annotations

import json

import httpx

from dehalu.adapters.llm import OpenAICompatibleLLMProvider, build_provider_registry
from dehalu.core.settings import Settings
from dehalu.schemas import (
    CoderOutput,
    CoVeResult,
    CoVeVerdict,
    ExtractedClaim,
    JudgeResult,
    JudgeVerdict,
    NormalizedRequest,
    PolicyDecision,
    PolicyDecisionState,
    RiskLevel,
    SandboxResult,
    SandboxStatus,
)


def _settings(**overrides: object) -> Settings:
    return Settings(database_url="sqlite://", groq_api_key="groq-key", **overrides)


def _request() -> NormalizedRequest:
    return NormalizedRequest(
        prompt="Write Python code.",
        language="python",
        risk_level=RiskLevel.medium,
        latency_budget_seconds=15,
        provider="groq",
    )


def _sandbox_result() -> SandboxResult:
    return SandboxResult(
        status=SandboxStatus.passed,
        check_type="compile_only",
        language="python",
        duration_ms=1.0,
    )


def _chat_response(text: str) -> dict[str, object]:
    return {"choices": [{"message": {"content": text}}]}


def test_build_provider_registry_adds_openai_compatible_providers() -> None:
    enabled = build_provider_registry(
        Settings(
            database_url="sqlite://",
            groq_api_key="groq-key",
            mistral_api_key="mistral-key",
            cerebras_api_key="cerebras-key",
        )
    )

    assert enabled.health() == {
        "fake": True,
        "groq": True,
        "mistral": True,
        "cerebras": True,
    }


def test_openai_compat_provider_clarify_generate_judge_cove_and_repair() -> None:
    responses = iter(
        [
            httpx.Response(
                200,
                json=_chat_response(
                    json.dumps(
                        {
                            "requested_outcome": "Write Python code.",
                            "language": "python",
                            "runtime_assumptions": [],
                            "constraints": [],
                            "acceptance_criteria": ["Return working Python code."],
                            "ambiguity_flags": [],
                            "needs_user_input": False,
                            "confidence": 0.9,
                        }
                    )
                ),
            ),
            httpx.Response(200, json=_chat_response("```python\nprint('ok')\n```")),
            httpx.Response(
                200,
                json=_chat_response(
                    json.dumps(
                        {
                            "verdict": "pass",
                            "hallucination_score": 0.1,
                            "findings": [],
                            "metrics": {"judge_mode": "panel"},
                        }
                    )
                ),
            ),
            httpx.Response(
                200,
                json=_chat_response(
                    json.dumps(
                        {
                            "checks": [
                                {
                                    "claim": "print('ok')",
                                    "question": "Does the generated output print ok?",
                                    "answer": "Yes.",
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
            httpx.Response(200, json=_chat_response("print('fixed')")),
        ]
    )
    client = httpx.Client(transport=httpx.MockTransport(lambda request: next(responses)))
    provider = OpenAICompatibleLLMProvider(
        name="groq",
        api_key="groq-key",
        base_url="https://api.x.ai/v1",
        generate_model="groq-code-fast-1",
        verify_model="groq-beta",
        timeout_seconds=15.0,
        http_client=client,
    )
    request = _request()

    clarification = provider.clarify(request)
    output = provider.generate(request)
    judge_result = provider.judge(request, output, [], [], _sandbox_result())
    cove_result = provider.cove(request, output, [ExtractedClaim(kind="code", value="print('ok')", source="code")], [], _sandbox_result(), judge_result)
    repaired = provider.repair(
        request,
        CoderOutput(provider="groq", model="groq-code-fast-1", language="python", code="print(eval(user_input))\n"),
        PolicyDecision(
            state=PolicyDecisionState.repair_and_retry,
            reasons=["Repair this."],
            hard_fail=False,
            score=0.6,
            metrics={"repair_trigger": "judge_fail"},
        ),
        JudgeResult(
            verdict=JudgeVerdict.fail,
            provider="groq",
            model="groq-beta",
            duration_ms=1.0,
            hallucination_score=0.8,
        ),
        CoVeResult(
            verdict=CoVeVerdict.fail,
            provider="groq",
            model="groq-beta",
            duration_ms=1.0,
            hallucination_score=0.8,
        ),
    )

    assert clarification.language == "python"
    assert clarification.metadata["provider_invocation"]["success"] is True
    assert output.code == "print('ok')"
    assert output.metadata["provider_invocation"]["prompt_template_version"] == "v1"
    assert judge_result.verdict == JudgeVerdict.pass_
    assert judge_result.metrics["provider_invocation"]["success"] is True
    assert cove_result.verdict.value == "pass"
    assert repaired.code == "print('fixed')"


def test_openai_compat_provider_retries_rate_limit_once() -> None:
    responses = iter(
        [
            httpx.Response(429, json={"error": {"message": "rate limited"}}),
            httpx.Response(200, json=_chat_response("print('ok')")),
        ]
    )
    client = httpx.Client(transport=httpx.MockTransport(lambda request: next(responses)))
    provider = OpenAICompatibleLLMProvider(
        name="groq",
        api_key="groq-key",
        base_url="https://api.x.ai/v1",
        generate_model="groq-code-fast-1",
        verify_model="groq-beta",
        timeout_seconds=15.0,
        http_client=client,
        retry_attempts=1,
    )

    output = provider.generate(_request())

    assert output.code == "print('ok')"
    assert output.metadata["provider_invocation"]["retry_count"] == 1
