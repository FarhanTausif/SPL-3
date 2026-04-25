from __future__ import annotations

from dehalu.schemas import SandboxStatus, StaticFindingSeverity
from dehalu.verification.sandbox import SandboxVerifier


def test_sandbox_compile_only_passes_valid_python() -> None:
    verifier = SandboxVerifier()

    result = verifier.verify("def f(value: int) -> int:\n    return value + 1\n", "python")

    assert result.status == SandboxStatus.passed
    assert result.check_type == "compile_only"
    assert result.language == "python"
    assert result.findings == []


def test_sandbox_compile_only_reports_python_syntax_error_location() -> None:
    verifier = SandboxVerifier()

    result = verifier.verify("def broken(:\n    return 1\n", "python")

    assert result.status == SandboxStatus.failed
    assert len(result.findings) == 1
    finding = result.findings[0]
    assert finding.code == "sandbox_compile_error"
    assert finding.severity == StaticFindingSeverity.error
    assert finding.line == 1
    assert finding.column is not None
    assert finding.message


def test_sandbox_compile_only_marks_unsupported_language_non_blocking() -> None:
    verifier = SandboxVerifier()

    result = verifier.verify("function f() { return 1; }", "javascript")

    assert result.status == SandboxStatus.unsupported
    assert len(result.findings) == 1
    assert result.findings[0].code == "sandbox_unsupported_language"
    assert result.findings[0].severity == StaticFindingSeverity.info
