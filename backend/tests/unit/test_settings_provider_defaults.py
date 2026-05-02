from __future__ import annotations

from dehalu.core.settings import Settings


def test_default_provider_auto_prefers_generation_order_live_provider() -> None:
    settings = Settings(database_url="sqlite://", default_provider="auto")

    selected = settings.resolve_default_provider(["fake", "gemini", "groq"])

    assert selected == "groq"


def test_default_provider_auto_falls_back_to_fake() -> None:
    settings = Settings(database_url="sqlite://", default_provider="auto")

    selected = settings.resolve_default_provider(["fake"])

    assert selected == "fake"


def test_default_provider_named_provider_falls_back_to_fake_when_unavailable() -> None:
    settings = Settings(database_url="sqlite://", default_provider="gemini")

    selected = settings.resolve_default_provider(["fake"])

    assert selected == "fake"
