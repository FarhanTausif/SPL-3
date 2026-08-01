from __future__ import annotations

import importlib.util
import re

from dehalu.api.schemas import Claim, StaticFinding


BUILTIN_CALLS = {
    "print",
    "len",
    "range",
    "str",
    "int",
    "float",
    "list",
    "dict",
    "set",
    "open",
    "map",
    "filter",
    "sum",
}


def validate_symbols(code: str, language: str, claims: list[Claim]) -> list[StaticFinding]:
    findings: list[StaticFinding] = []
    imports = {claim.claim_text.split(".")[0] for claim in claims if claim.claim_type == "dependency"}
    defined = _defined_symbols(code)

    for claim in claims:
        if claim.claim_type == "dependency":
            if _looks_fake(claim.claim_text) or (language == "python" and not _python_import_exists(claim.claim_text)):
                claim.status = "unsupported"
                findings.append(
                    StaticFinding(
                        rule_id="symbol-indexer.unresolved-import",
                        severity="error",
                        message=f"Dependency `{claim.claim_text}` could not be resolved.",
                        location=claim.location,
                        evidence_source="Symbol Indexer/API Validator",
                    )
                )
            else:
                claim.status = "supported"
        elif claim.claim_type == "api":
            root = claim.claim_text.split(".")[0]
            if root and root not in imports and root not in defined and root not in BUILTIN_CALLS:
                claim.status = "uncertain"
                findings.append(
                    StaticFinding(
                        rule_id="symbol-indexer.invalid-reference",
                        severity="warning",
                        message=f"Reference `{claim.claim_text}` is not locally defined or imported.",
                        location=claim.location,
                        evidence_source="Symbol Indexer/API Validator",
                    )
                )
            elif "." in claim.claim_text and _looks_fake(claim.claim_text):
                claim.status = "unsupported"
                findings.append(
                    StaticFinding(
                        rule_id="symbol-indexer.api-conflict",
                        severity="error",
                        message=f"API `{claim.claim_text}` appears invented or incompatible.",
                        location=claim.location,
                        evidence_source="Symbol Indexer/API Validator",
                    )
                )
            else:
                claim.status = "supported"
    return findings


def _defined_symbols(code: str) -> set[str]:
    symbols = set(re.findall(r"\b(?:def|function|class)\s+([A-Za-z_]\w*)", code))
    symbols.update(re.findall(r"^\s*([A-Za-z_]\w*)\s*=", code, re.MULTILINE))
    return symbols


def _python_import_exists(module: str) -> bool:
    root = module.split(".")[0]
    try:
        return importlib.util.find_spec(root) is not None
    except (ImportError, ValueError):
        return False


def _looks_fake(value: str) -> bool:
    lower = value.lower()
    return any(marker in lower for marker in ["fake", "nonexistent", "madeup", "magic_call", "404"])
