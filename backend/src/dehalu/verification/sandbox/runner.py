from __future__ import annotations

from time import perf_counter

from dehalu.schemas import SandboxResult, SandboxStatus, StaticFinding, StaticFindingSeverity


class SandboxVerifier:
    check_type = "compile_only"

    def verify(self, code: str, language: str) -> SandboxResult:
        started_at = perf_counter()
        normalized_language = language.lower()

        if normalized_language != "python":
            return SandboxResult(
                status=SandboxStatus.unsupported,
                check_type=self.check_type,
                language=normalized_language,
                duration_ms=self._duration_ms(started_at),
                findings=[
                    StaticFinding(
                        code="sandbox_unsupported_language",
                        message=f"No compile-only sandbox exists for language '{language}'.",
                        severity=StaticFindingSeverity.info,
                        metadata={
                            "language": normalized_language,
                            "check_type": self.check_type,
                        },
                    )
                ],
            )

        try:
            compile(code, "<dehalu-sandbox>", "exec")
        except SyntaxError as exc:
            return SandboxResult(
                status=SandboxStatus.failed,
                check_type=self.check_type,
                language=normalized_language,
                duration_ms=self._duration_ms(started_at),
                findings=[
                    StaticFinding(
                        code="sandbox_compile_error",
                        message=exc.msg,
                        severity=StaticFindingSeverity.error,
                        line=exc.lineno,
                        column=exc.offset,
                        metadata={
                            "filename": exc.filename,
                            "check_type": self.check_type,
                        },
                    )
                ],
            )

        return SandboxResult(
            status=SandboxStatus.passed,
            check_type=self.check_type,
            language=normalized_language,
            duration_ms=self._duration_ms(started_at),
            findings=[],
        )

    def _duration_ms(self, started_at: float) -> float:
        return round((perf_counter() - started_at) * 1000, 3)
