from __future__ import annotations

from dehalu.adapters.language import build_language_registry
from dehalu.schemas import CoderOutput
from dehalu.verification.claims import ClaimExtractor


def test_python_claim_extraction_reads_code_imports_symbols_and_assumptions() -> None:
    extractor = ClaimExtractor(build_language_registry())
    output = CoderOutput(
        provider="fake",
        model="fake",
        language="python",
        code="import math\n\ndef f(x):\n    return math.sqrt(x)\n",
        assumptions=["Python 3.12 runtime"],
        dependencies=["math"],
    )

    claims = extractor.extract(output)
    claim_pairs = {(claim.kind, claim.value) for claim in claims}

    assert ("code", output.code) in claim_pairs
    assert ("dependency", "math") in claim_pairs
    assert ("assumption", "Python 3.12 runtime") in claim_pairs
    assert ("import", "math") in claim_pairs
    assert ("symbol", "math.sqrt") in claim_pairs


def test_claim_extraction_handles_malformed_python_without_crashing() -> None:
    extractor = ClaimExtractor(build_language_registry())
    output = CoderOutput(
        provider="fake",
        model="fake",
        language="python",
        code="def broken(:\n",
        assumptions=["Malformed code is still captured as a code claim."],
    )

    claims = extractor.extract(output)

    assert [claim.kind for claim in claims].count("code") == 1
    assert any(claim.kind == "assumption" for claim in claims)

