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
    return Settings(database_url="sqlite://", grok_api_key="grok-key", **overrides)


def _request() -> NormalizedRequest:
    return NormalizedRequest(
        prompt="Write Python code.",
        language="python",
        risk_level=RiskLevel.medium,
        latency_budget_seconds=15,
        provider="grok",
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
            grok_api_key="grok-key",
            mistral_api_key="mistral-key",
            cerebras_api_key="cerebras-key",
        )
    )

    assert enabled.health() == {
        "fake": True,
        "grok": True,
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
        name="grok",
        api_key="grok-key",
        base_url="https://api.x.ai/v1",
        generate_model="grok-code-fast-1",
        verify_model="grok-beta",
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
        CoderOutput(provider="grok", model="grok-code-fast-1", language="python", code="print(eval(user_input))\n"),
        PolicyDecision(
            state=PolicyDecisionState.repair_and_retry,
            reasons=["Repair this."],
            hard_fail=False,
            score=0.6,
            metrics={"repair_trigger": "judge_fail"},
        ),
        JudgeResult(
            verdict=JudgeVerdict.fail,
            provider="grok",
            model="grok-beta",
            duration_ms=1.0,
            hallucination_score=0.8,
        ),
        CoVeResult(
            verdict=CoVeVerdict.fail,
            provider="grok",
            model="grok-beta",
            duration_ms=1.0,
            hallucination_score=0.8,
        ),
    )

    assert clarification.language == "python"
    assert output.code == "print('ok')"
    assert judge_result.verdict == JudgeVerdict.pass_
    assert cove_result.verdict.value == "pass"
    assert repaired.code == "print('fixed')"
