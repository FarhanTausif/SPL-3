from __future__ import annotations

from dehalu.adapters.llm.fake import FakeLLMProvider
from dehalu.schemas import (
    CoderOutput,
    CoVeCheckVerdict,
    CoVeVerdict,
    ExtractedClaim,
    JudgeResult,
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


def _judge_result() -> JudgeResult:
    return JudgeResult(
        verdict=JudgeVerdict.pass_,
        provider="fake",
        model="fake",
        duration_ms=1.0,
        hallucination_score=0.05,
    )


def _output(code: str, language: str = "python", assumptions: list[str] | None = None) -> CoderOutput:
    return CoderOutput(
        provider="fake",
        model="fake",
        language=language,
        code=code,
        assumptions=assumptions or [],
    )


def test_fake_cove_passes_clean_python_output() -> None:
    provider = FakeLLMProvider()
    request = _request()
    output = provider.generate(request)
    claims = [
        ExtractedClaim(kind="import", value="math", source="code"),
        ExtractedClaim(kind="symbol", value="math.sqrt", source="code"),
    ]

    result = provider.cove(request, output, claims, [], _sandbox_result(), _judge_result())

    assert result.verdict == CoVeVerdict.pass_
    assert result.hallucination_score == 0.05
    assert all(check.verdict == CoVeCheckVerdict.supported for check in result.checks)


def test_fake_cove_is_uncertain_for_unsafe_constructs() -> None:
    provider = FakeLLMProvider()
    request = _request()
    output = _output("def f(user_input: str):\n    return eval(user_input)\n")
    claims = [ExtractedClaim(kind="code", value=output.code, source="code")]

    result = provider.cove(request, output, claims, [], _sandbox_result(), _judge_result())

    assert result.verdict == CoVeVerdict.uncertain
    assert any(check.verdict == CoVeCheckVerdict.uncertain for check in result.checks)
    assert any(finding.code == "cove_uncertain_claim" for finding in result.findings)


def test_fake_cove_fails_contradictory_claims() -> None:
    provider = FakeLLMProvider()
    request = _request()
    output = _output("def generated_example(value: float) -> float:\n    return value\n")
    claims = [ExtractedClaim(kind="symbol", value="math.sqrt", source="code")]

    result = provider.cove(request, output, claims, [], _sandbox_result(), _judge_result())

    assert result.verdict == CoVeVerdict.fail
    assert any(check.verdict == CoVeCheckVerdict.unsupported for check in result.checks)
    assert any(finding.code == "cove_unsupported_claim" for finding in result.findings)


def test_fake_cove_maps_claims_to_structured_checks() -> None:
    provider = FakeLLMProvider()
    request = _request()
    output = _output(
        "import math\n\ndef generated_example(value: float) -> float:\n    return math.sqrt(value)\n",
        assumptions=["Python 3.12 runtime"],
    )
    claims = [
        ExtractedClaim(kind="dependency", value="math", source="metadata"),
        ExtractedClaim(kind="assumption", value="Python 3.12 runtime", source="metadata"),
    ]

    result = provider.cove(request, output, claims, [], _sandbox_result(), _judge_result())

    assert [check.claim for check in result.checks] == ["math", "Python 3.12 runtime"]
    assert all(check.question for check in result.checks)
    assert result.metrics["supported_claim_count"] == 2
