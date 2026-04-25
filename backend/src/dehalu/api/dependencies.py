from __future__ import annotations

from functools import lru_cache

from dehalu.adapters.llm import ProviderRegistry, build_provider_registry
from dehalu.core.settings import Settings, get_settings
from dehalu.orchestration import RunOrchestrator


@lru_cache
def _get_provider_registry() -> ProviderRegistry:
    return build_provider_registry(get_settings())


async def get_provider_registry() -> ProviderRegistry:
    return _get_provider_registry()


async def get_orchestrator() -> RunOrchestrator:
    settings = get_settings()
    return RunOrchestrator(settings, _get_provider_registry())


async def get_app_settings() -> Settings:
    return get_settings()
