from __future__ import annotations

from dehalu.adapters.language import LanguageAdapterRegistry
from dehalu.schemas import CoderOutput, ExtractedClaim


class ClaimExtractor:
    def __init__(self, language_registry: LanguageAdapterRegistry) -> None:
        self.language_registry = language_registry

    def extract(self, coder_output: CoderOutput) -> list[ExtractedClaim]:
        adapter = self.language_registry.get(coder_output.language)
        claims = [
            ExtractedClaim(
                kind="code",
                value=coder_output.code,
                source="coder_output.code",
                metadata={"language": coder_output.language},
            )
        ]

        claims.extend(
            ExtractedClaim(kind="dependency", value=dependency, source="coder_output.dependencies")
            for dependency in coder_output.dependencies
        )
        claims.extend(
            ExtractedClaim(kind="assumption", value=assumption, source="coder_output.assumptions")
            for assumption in coder_output.assumptions
        )
        claims.extend(
            ExtractedClaim(
                kind="import",
                value=import_ref.name,
                source="static_parse.import",
                metadata={"line": import_ref.line, "column": import_ref.column},
            )
            for import_ref in adapter.extract_imports(coder_output.code)
            if import_ref.name
        )
        claims.extend(
            ExtractedClaim(
                kind="symbol",
                value=symbol.name,
                source="static_parse.symbol",
                metadata={
                    "line": symbol.line,
                    "column": symbol.column,
                    **symbol.metadata,
                },
            )
            for symbol in adapter.extract_symbols(coder_output.code)
            if symbol.name
        )
        return claims

