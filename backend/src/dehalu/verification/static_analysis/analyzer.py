from __future__ import annotations

from dehalu.adapters.language import LanguageAdapterRegistry
from dehalu.schemas import StaticFinding, StaticFindingSeverity


class StaticAnalyzer:
    dangerous_symbols = {
        "eval": "Dynamic eval can execute untrusted code.",
        "exec": "Dynamic exec can execute untrusted code.",
        "os.system": "Shell execution is unsupported in the first backend slice.",
        "subprocess.Popen": "Process spawning is unsupported in the first backend slice.",
        "subprocess.run": "Process spawning is unsupported in the first backend slice.",
    }

    def __init__(self, language_registry: LanguageAdapterRegistry) -> None:
        self.language_registry = language_registry

    def analyze(self, code: str, language: str) -> list[StaticFinding]:
        adapter = self.language_registry.get(language)
        if adapter.language == "generic":
            return [
                StaticFinding(
                    code="unsupported_language",
                    message=f"No concrete static analyzer exists for language '{language}'.",
                    severity=StaticFindingSeverity.warning,
                    metadata={"language": language},
                )
            ]

        parse_result = adapter.parse(code)
        if not parse_result.ok:
            error = parse_result.error
            return [
                StaticFinding(
                    code="syntax_error",
                    message=error.msg if error else "Syntax parsing failed.",
                    severity=StaticFindingSeverity.error,
                    line=error.lineno if error else None,
                    column=error.offset if error else None,
                    metadata={"language": language},
                )
            ]

        findings: list[StaticFinding] = []
        imports = adapter.extract_imports(code)
        findings.extend(
            StaticFinding(
                code="import_detected",
                message=f"Import detected: {import_ref.name}",
                severity=StaticFindingSeverity.info,
                line=import_ref.line,
                column=import_ref.column,
                metadata={"import": import_ref.name},
            )
            for import_ref in imports
            if import_ref.name
        )

        for symbol in adapter.extract_symbols(code):
            reason = self.dangerous_symbols.get(symbol.name)
            if reason:
                findings.append(
                    StaticFinding(
                        code="dangerous_symbol",
                        message=reason,
                        severity=StaticFindingSeverity.warning,
                        line=symbol.line,
                        column=symbol.column,
                        metadata={"symbol": symbol.name},
                    )
                )

        return findings

