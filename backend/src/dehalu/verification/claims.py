from __future__ import annotations

import re

from dehalu.api.schemas import Claim


IMPORT_PATTERNS = [
    re.compile(r"^\s*import\s+([a-zA-Z_][\w.]*)", re.MULTILINE),
    re.compile(r"^\s*from\s+([a-zA-Z_][\w.]*)\s+import\s+([\w*,\s]+)", re.MULTILINE),
    re.compile(r"^\s*(?:const|let|var)\s+\w+\s*=\s*require\(['\"]([^'\"]+)['\"]\)", re.MULTILINE),
    re.compile(r"^\s*import\s+.*?\s+from\s+['\"]([^'\"]+)['\"]", re.MULTILINE),
]


def extract_claims(code: str, explanation: str = "") -> list[Claim]:
    claims: list[Claim] = []
    lines = code.splitlines()

    for index, line in enumerate(lines, start=1):
        for pattern in IMPORT_PATTERNS:
            for match in pattern.finditer(line):
                claims.append(
                    Claim(
                        claim_type="dependency",
                        claim_text=match.group(1),
                        location=f"line {index}",
                    )
                )
        for call in re.finditer(r"\b([A-Za-z_][\w.]*?)\s*\(", line):
            name = call.group(1)
            if name not in {"if", "for", "while", "return", "switch", "catch", "function"}:
                claims.append(Claim(claim_type="api", claim_text=name, location=f"line {index}"))
        for definition in re.finditer(r"\b(?:def|function|class)\s+([A-Za-z_]\w*)", line):
            claims.append(
                Claim(claim_type="symbol", claim_text=definition.group(1), location=f"line {index}", status="supported")
            )

    for sentence in re.split(r"[.\n]", explanation):
        clean = sentence.strip()
        if len(clean.split()) >= 5:
            claims.append(Claim(claim_type="behavior", claim_text=clean, location="explanation"))

    seen: set[tuple[str, str, str]] = set()
    unique: list[Claim] = []
    for claim in claims:
        key = (claim.claim_type, claim.claim_text, claim.location)
        if key not in seen:
            seen.add(key)
            unique.append(claim)
    return unique
