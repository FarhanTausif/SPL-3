from __future__ import annotations

from dehalu.adapters.language.base import LanguageAdapter
from dehalu.adapters.language.generic import GenericLanguageAdapter
from dehalu.adapters.language.python import PythonLanguageAdapter


class LanguageAdapterRegistry:
    def __init__(self, adapters: list[LanguageAdapter], fallback: LanguageAdapter) -> None:
        self._adapters = {adapter.language: adapter for adapter in adapters}
        self._fallback = fallback

    def get(self, language: str) -> LanguageAdapter:
        return self._adapters.get(language.lower(), self._fallback)


def build_language_registry() -> LanguageAdapterRegistry:
    generic = GenericLanguageAdapter()
    return LanguageAdapterRegistry([PythonLanguageAdapter()], generic)

