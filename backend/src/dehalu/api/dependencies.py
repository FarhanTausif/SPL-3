from __future__ import annotations

from dehalu.adapters.llm import ProviderRegistry, build_provider_registry
from dehalu.core.settings import Settings, get_settings
from dehalu.orchestration import RunOrchestrator

_provider_registry = build_provider_registry()


async def get_provider_registry() -> ProviderRegistry:
    return _provider_registry


async def get_orchestrator() -> RunOrchestrator:
    return RunOrchestrator(get_settings(), _provider_registry)


async def get_app_settings() -> Settings:
    return get_settings()
