from __future__ import annotations

import httpx

from dehalu.adapters.llm.base import LLMProvider
from dehalu.adapters.llm.fake import FakeLLMProvider
from dehalu.adapters.llm.gemini import GeminiLLMProvider
from dehalu.core.settings import Settings


class UnknownProviderError(ValueError):
    pass


class ProviderRegistry:
    def __init__(self, providers: list[LLMProvider]) -> None:
        self._providers = {provider.name: provider for provider in providers}

    def get(self, provider_name: str) -> LLMProvider:
        try:
            return self._providers[provider_name]
        except KeyError as exc:
            raise UnknownProviderError(provider_name) from exc

    def health(self) -> dict[str, bool]:
        return {name: provider.healthcheck() for name, provider in self._providers.items()}


def build_provider_registry(
    settings: Settings | None = None,
    *,
    gemini_http_client: httpx.Client | None = None,
) -> ProviderRegistry:
    settings = settings or Settings()
    providers: list[LLMProvider] = [FakeLLMProvider()]
    if settings.gemini_enabled:
        providers.append(GeminiLLMProvider(settings, http_client=gemini_http_client))
    return ProviderRegistry(providers)
