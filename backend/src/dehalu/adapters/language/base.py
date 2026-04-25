from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class ParseResult:
    ok: bool
    tree: Any | None = None
    error: SyntaxError | None = None


@dataclass(frozen=True)
class ImportReference:
    name: str
    line: int | None = None
    column: int | None = None


@dataclass(frozen=True)
class SymbolReference:
    name: str
    line: int | None = None
    column: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class LanguageAdapter(Protocol):
    language: str

    def parse(self, code: str) -> ParseResult:
        raise NotImplementedError

    def extract_imports(self, code: str) -> list[ImportReference]:
        raise NotImplementedError

    def extract_symbols(self, code: str) -> list[SymbolReference]:
        raise NotImplementedError

