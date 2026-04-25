from __future__ import annotations

from dehalu.adapters.llm.base import LLMProvider
from dehalu.adapters.llm.fake import FakeLLMProvider


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


def build_provider_registry() -> ProviderRegistry:
    return ProviderRegistry([FakeLLMProvider()])

