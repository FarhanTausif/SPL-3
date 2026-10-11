"""Resolve the three judge roles consistently across runtime and diagnostics."""
from dataclasses import dataclass, field

from dehalu.core.settings import Settings


@dataclass(frozen=True)
class JudgeSpec:
    name: str
    provider: str
    model: str
    key: str | None = field(repr=False)
    role: str


def judge_specs(settings: Settings) -> tuple[JudgeSpec, ...]:
    provider = settings.quality_safety_provider
    return (
        JudgeSpec('gemini', 'gemini', settings.gemini_model, settings.gemini_api_key, 'requirement_alignment'),
        JudgeSpec('groq', 'groq', settings.groq_model, settings.groq_api_key, 'functional_logic'),
        JudgeSpec(
            'gemini (quality/safety)' if provider == 'gemini' else 'mistral',
            provider, getattr(settings, f'{provider}_model'), getattr(settings, f'{provider}_api_key'),
            'quality_safety',
        ),
    )
