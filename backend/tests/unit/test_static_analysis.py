from __future__ import annotations

from dehalu.adapters.language import build_language_registry
from dehalu.schemas import StaticFindingSeverity
from dehalu.verification.static_analysis import StaticAnalyzer


def test_static_analysis_accepts_valid_python() -> None:
    analyzer = StaticAnalyzer(build_language_registry())

    findings = analyzer.analyze("import math\nx = math.sqrt(4)\n", "python")

    assert not any(finding.severity == StaticFindingSeverity.error for finding in findings)
    assert any(finding.code == "import_detected" for finding in findings)


def test_static_analysis_rejects_python_syntax_error() -> None:
    analyzer = StaticAnalyzer(build_language_registry())

    findings = analyzer.analyze("def broken(:\n", "python")

    assert findings[0].code == "syntax_error"
    assert findings[0].severity == StaticFindingSeverity.error


def test_static_analysis_flags_dangerous_symbol() -> None:
    analyzer = StaticAnalyzer(build_language_registry())

    findings = analyzer.analyze("def f(user_input):\n    return eval(user_input)\n", "python")

    assert any(finding.code == "dangerous_symbol" for finding in findings)


def test_static_analysis_unknown_language_uses_fallback() -> None:
    analyzer = StaticAnalyzer(build_language_registry())

    findings = analyzer.analyze("function f() { return 1; }", "javascript")

    assert findings[0].code == "unsupported_language"
    assert findings[0].severity == StaticFindingSeverity.warning

