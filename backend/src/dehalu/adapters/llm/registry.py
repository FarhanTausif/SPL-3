from __future__ import annotations

import httpx

from dehalu.adapters.llm.base import LLMProvider
from dehalu.adapters.llm.fake import FakeLLMProvider
from dehalu.adapters.llm.gemini import GeminiLLMProvider
from dehalu.adapters.llm.openai_compat import OpenAICompatibleLLMProvider
from dehalu.core.settings import Settings


class UnknownProviderError(ValueError):
    pass


class ProviderRegistry:
    def __init__(self, providers: list[LLMProvider]) -> None:
        self._providers = {provider.name: provider for provider in providers}

    def names(self) -> list[str]:
        return list(self._providers)

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
    grok_http_client: httpx.Client | None = None,
    mistral_http_client: httpx.Client | None = None,
    cerebras_http_client: httpx.Client | None = None,
) -> ProviderRegistry:
    settings = settings or Settings()
    providers: list[LLMProvider] = [FakeLLMProvider()]
    if settings.gemini_enabled:
        providers.append(GeminiLLMProvider(settings, http_client=gemini_http_client))
    if settings.grok_enabled:
        providers.append(
            OpenAICompatibleLLMProvider(
                name="grok",
                api_key=settings.grok_api_key,
                base_url=settings.grok_base_url,
                generate_model=settings.grok_generate_model,
                verify_model=settings.grok_verify_model,
                timeout_seconds=settings.grok_timeout_seconds,
                http_client=grok_http_client,
            )
        )
    if settings.mistral_enabled:
        providers.append(
            OpenAICompatibleLLMProvider(
                name="mistral",
                api_key=settings.mistral_api_key,
                base_url=settings.mistral_base_url,
                generate_model=settings.mistral_generate_model,
                verify_model=settings.mistral_verify_model,
                timeout_seconds=settings.mistral_timeout_seconds,
                http_client=mistral_http_client,
            )
        )
    if settings.cerebras_enabled:
        providers.append(
            OpenAICompatibleLLMProvider(
                name="cerebras",
                api_key=settings.cerebras_api_key,
                base_url=settings.cerebras_base_url,
                generate_model=settings.cerebras_generate_model,
                verify_model=settings.cerebras_verify_model,
                timeout_seconds=settings.cerebras_timeout_seconds,
                http_client=cerebras_http_client,
            )
        )
    return ProviderRegistry(providers)
