from __future__ import annotations

import ast

from dehalu.adapters.language.base import ImportReference, ParseResult, SymbolReference


class PythonLanguageAdapter:
    language = "python"

    def parse(self, code: str) -> ParseResult:
        try:
            return ParseResult(ok=True, tree=ast.parse(code))
        except SyntaxError as exc:
            return ParseResult(ok=False, error=exc)

    def extract_imports(self, code: str) -> list[ImportReference]:
        parse_result = self.parse(code)
        if not parse_result.ok or parse_result.tree is None:
            return []

        imports: list[ImportReference] = []
        for node in ast.walk(parse_result.tree):
            if isinstance(node, ast.Import):
                imports.extend(
                    ImportReference(name=alias.name, line=node.lineno, column=node.col_offset)
                    for alias in node.names
                )
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                imports.append(ImportReference(name=module, line=node.lineno, column=node.col_offset))
        return imports

    def extract_symbols(self, code: str) -> list[SymbolReference]:
        parse_result = self.parse(code)
        if not parse_result.ok or parse_result.tree is None:
            return []

        symbols: list[SymbolReference] = []
        for node in ast.walk(parse_result.tree):
            if isinstance(node, ast.Call):
                name = self._call_name(node.func)
                if name:
                    symbols.append(
                        SymbolReference(
                            name=name,
                            line=node.lineno,
                            column=node.col_offset,
                            metadata={"usage": "call"},
                        )
                    )
            elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                symbols.append(
                    SymbolReference(
                        name=node.id,
                        line=node.lineno,
                        column=node.col_offset,
                        metadata={"usage": "load"},
                    )
                )
        return symbols

    def _call_name(self, node: ast.expr) -> str | None:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            parent = self._call_name(node.value)
            return f"{parent}.{node.attr}" if parent else node.attr
        return None

