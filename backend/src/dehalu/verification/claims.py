from dehalu.domain.models import Claim
from dehalu.verification.adapters import get_adapter


def extract_claims(code: str, explanation: str = "", language: str = "python") -> list[Claim]:
    adapter = get_adapter(language)
    return adapter.extract(code) if adapter else []
