from __future__ import annotations

from dehalu.adapters.language.base import ImportReference, ParseResult, SymbolReference


class GenericLanguageAdapter:
    language = "generic"

    def parse(self, code: str) -> ParseResult:
        return ParseResult(ok=True, tree=None)

    def extract_imports(self, code: str) -> list[ImportReference]:
        return []

    def extract_symbols(self, code: str) -> list[SymbolReference]:
        return []

