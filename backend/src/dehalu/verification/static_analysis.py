from __future__ import annotations

import ast
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from dehalu.api.schemas import StaticFinding


RISKY_PATTERNS = {
    "unsafe-shell": [r"\bos\.system\s*\(", r"\bsubprocess\.", r"\bexec\s*\(", r"\beval\s*\("],
    "unsafe-file-delete": [r"\brm\s+-rf\b", r"\bunlink\s*\(", r"\brmtree\s*\("],
    "unsafe-network": [r"\brequests\.", r"\bfetch\s*\(", r"\bhttpx\."],
    "secret-handling": [r"api[_-]?key\s*=", r"password\s*=", r"token\s*="],
}


def run_static_analysis(code: str, language: str) -> list[StaticFinding]:
    staged = run_static_analysis_by_stage(code, language)
    return staged["tree_sitter"] + staged["semgrep"]


def run_static_analysis_by_stage(code: str, language: str) -> dict[str, list[StaticFinding]]:
    return {
        "tree_sitter": _tree_sitter_or_fallback(code, language),
        "semgrep": _semgrep_or_fallback(code, language) + _generic_quality_checks(code),
    }


def _tree_sitter_or_fallback(code: str, language: str) -> list[StaticFinding]:
    if language.lower() == "python":
        try:
            ast.parse(code)
        except SyntaxError as exc:
            return [
                StaticFinding(
                    rule_id="tree-sitter.syntax",
                    severity="error",
                    message=f"Syntax or incomplete-code finding: {exc.msg}",
                    location=f"line {exc.lineno or 1}",
                    evidence_source="Tree-sitter/AST fallback",
                )
            ]
    stack = []
    pairs = {")": "(", "]": "[", "}": "{"}
    for index, char in enumerate(code):
        if char in "([{":
            stack.append(char)
        elif char in ")]}":
            if not stack or stack.pop() != pairs[char]:
                return [
                    StaticFinding(
                        rule_id="tree-sitter.structure",
                        severity="error",
                        message="Unbalanced or malformed delimiter structure detected.",
                        location=f"offset {index}",
                        evidence_source="Tree-sitter/generic fallback",
                    )
                ]
    if stack:
        return [
            StaticFinding(
                rule_id="tree-sitter.incomplete",
                severity="error",
                message="Incomplete code structure detected from unclosed delimiters.",
                location="end of file",
                evidence_source="Tree-sitter/generic fallback",
            )
        ]
    return []


def _semgrep_or_fallback(code: str, language: str) -> list[StaticFinding]:
    if shutil.which("semgrep"):
        suffix = {
            "python": ".py",
            "javascript": ".js",
            "typescript": ".ts",
            "java": ".java",
            "go": ".go",
            "rust": ".rs",
        }.get(language.lower(), ".txt")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / f"snippet{suffix}"
            path.write_text(code, encoding="utf-8")
            result = subprocess.run(
                ["semgrep", "--config", "auto", "--json", str(path)],
                check=False,
                capture_output=True,
                text=True,
                timeout=20,
            )
            if result.returncode in {0, 1} and result.stdout:
                return [
                    StaticFinding(
                        rule_id="semgrep.scan",
                        severity="info",
                        message="Semgrep completed; inspect raw scanner output in logs if enabled.",
                        location="snippet",
                        evidence_source="Semgrep/SAST",
                    )
                ]
    findings: list[StaticFinding] = []
    for rule_id, patterns in RISKY_PATTERNS.items():
        for pattern in patterns:
            for match in re.finditer(pattern, code, flags=re.I):
                line = code[: match.start()].count("\n") + 1
                findings.append(
                    StaticFinding(
                        rule_id=f"semgrep.{rule_id}",
                        severity="warning" if rule_id != "unsafe-shell" else "error",
                        message=f"Static unsafe-pattern finding for `{match.group(0)}`.",
                        location=f"line {line}",
                        evidence_source="Semgrep/SAST fallback",
                    )
                )
    return findings


def _generic_quality_checks(code: str) -> list[StaticFinding]:
    findings: list[StaticFinding] = []
    if "TODO" in code or "pass\n" in code:
        findings.append(
            StaticFinding(
                rule_id="quality.incomplete-placeholder",
                severity="warning",
                message="Placeholder or incomplete implementation marker detected.",
                location="snippet",
                evidence_source="Static quality heuristic",
            )
        )
    return findings
