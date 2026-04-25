from __future__ import annotations

from dehalu.adapters.llm.fake import FakeLLMProvider
from dehalu.schemas import (
    CoderOutput,
    JudgeVerdict,
    NormalizedRequest,
    RiskLevel,
    SandboxResult,
    SandboxStatus,
)


def _request(language: str = "python") -> NormalizedRequest:
    return NormalizedRequest(
        prompt="Write Python code.",
        language=language,
        risk_level=RiskLevel.medium,
        latency_budget_seconds=15,
        provider="fake",
    )


def _sandbox_result(language: str = "python") -> SandboxResult:
    return SandboxResult(
        status=SandboxStatus.passed,
        check_type="compile_only",
        language=language,
        duration_ms=1.0,
    )


def _output(code: str, language: str = "python") -> CoderOutput:
    return CoderOutput(
        provider="fake",
        model="fake",
        language=language,
        code=code,
    )


def test_fake_judge_passes_clean_python_output() -> None:
    provider = FakeLLMProvider()
    request = _request()
    output = provider.generate(request)

    result = provider.judge(request, output, [], [], _sandbox_result())

    assert result.verdict == JudgeVerdict.pass_
    assert result.hallucination_score == 0.05
    assert result.findings == []


def test_fake_judge_is_uncertain_for_unsafe_constructs() -> None:
    provider = FakeLLMProvider()
    request = _request()
    output = _output("def f(user_input: str):\n    return eval(user_input)\n")

    result = provider.judge(request, output, [], [], _sandbox_result())

    assert result.verdict == JudgeVerdict.uncertain
    assert result.hallucination_score == 0.55
    assert any(finding.code == "unsafe_or_unverifiable_construct" for finding in result.findings)


def test_fake_judge_fails_empty_output() -> None:
    provider = FakeLLMProvider()
    request = _request()
    output = _output("")

    result = provider.judge(request, output, [], [], _sandbox_result())

    assert result.verdict == JudgeVerdict.fail
    assert result.hallucination_score == 0.9
    assert any(finding.code == "empty_output" for finding in result.findings)


def test_fake_judge_fails_language_mismatch() -> None:
    provider = FakeLLMProvider()
    request = _request("python")
    output = _output("function f() { return 1; }\n", "javascript")

    result = provider.judge(request, output, [], [], _sandbox_result("javascript"))

    assert result.verdict == JudgeVerdict.fail
    assert any(finding.code == "language_mismatch" for finding in result.findings)
