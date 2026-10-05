"""Language adapters parse source only; no imports or generated code are executed."""
from __future__ import annotations
import ast
import builtins
from dataclasses import dataclass
from functools import lru_cache
from dehalu.domain.models import AnalyzerCoverage, Claim, StaticFinding

LANGUAGES = ("python", "javascript", "typescript", "java", "go", "rust", "c", "cpp")
ALIASES = {"js": "javascript", "ts": "typescript", "c++": "cpp", "golang": "go", "py": "python", "jsx": "javascript", "tsx": "typescript"}
# Grammar-specific nodes and fields isolate language assumptions from the pipeline.
NODES = {
    "javascript": (("import_statement",), ("function_declaration", "class_declaration", "variable_declarator"), ("call_expression",)),
    "typescript": (("import_statement",), ("function_declaration", "class_declaration", "variable_declarator", "interface_declaration", "type_alias_declaration"), ("call_expression",)),
    "java": (("import_declaration",), ("class_declaration", "method_declaration", "variable_declarator"), ("method_invocation", "object_creation_expression")),
    "go": (("import_spec",), ("function_declaration", "method_declaration", "type_spec", "var_spec"), ("call_expression",)),
    "rust": (("use_declaration", "extern_crate_declaration"), ("function_item", "struct_item", "let_declaration"), ("call_expression", "macro_invocation")),
    "c": (("preproc_include",), ("function_definition", "declaration"), ("call_expression",)),
    "cpp": (("preproc_include", "using_declaration"), ("function_definition", "class_specifier", "declaration"), ("call_expression",)),
}


def normalize(language: str) -> str:
    return ALIASES.get(language.lower(), language.lower())


@lru_cache(maxsize=12)
def grammar(language: str):
    from tree_sitter_language_pack import get_language
    return get_language(language)


def parser(language: str, code: str):
    from tree_sitter import Parser
    name = "tsx" if language == "typescript" else language
    return Parser(grammar(name)).parse(code.encode())


def walk(node):
    yield node
    for child in node.named_children:
        yield from walk(child)


def span(node) -> dict[str, int]:
    return {"start_line": node.start_point.row + 1, "start_column": node.start_point.column + 1,
            "end_line": node.end_point.row + 1, "end_column": node.end_point.column + 1}


def text(node) -> str:
    return node.text.decode() if node else ""


@dataclass
class LanguageAdapter:
    language: str

    def parse(self, code: str) -> tuple[list[StaticFinding], AnalyzerCoverage]:
        try:
            tree = parser(self.language, code)
            findings = [StaticFinding(rule_id="tree-sitter.syntax", severity="error",
                message=f"Malformed or incomplete syntax: {text(n)[:100] or 'missing ' + n.type}",
                location=f"line {n.start_point.row + 1}", source_range=span(n), evidence_source="Tree-sitter 0.25.2")
                for n in walk(tree.root_node) if n.type == "ERROR" or n.is_missing]
            if not code.strip():
                findings.append(StaticFinding(rule_id="tree-sitter.empty", severity="error", message="Empty generated code.", evidence_source="Parser"))
            if self.language == "python":
                try:
                    ast.parse(code)
                except SyntaxError as exc:
                    if not findings:
                        findings.append(StaticFinding(rule_id="tree-sitter.syntax", severity="error", message=exc.msg,
                            location=f"line {exc.lineno}", evidence_source="Python AST"))
            return findings, AnalyzerCoverage(analyzer="parser", language=self.language, status="available", detail="Pinned grammar with error/missing-node detection", version="0.25.2/0.9.0")
        except (ImportError, LookupError, ValueError) as exc:
            return [], AnalyzerCoverage(analyzer="parser", language=self.language, status="unavailable", detail=str(exc))

    def extract(self, code: str) -> list[Claim]:
        if self.language == "python":
            return python_claims(code)
        try:
            tree = parser(self.language, code)
            from tree_sitter import Query, QueryCursor
            imports, definitions, calls = NODES[self.language]
            query = Query(grammar("tsx" if self.language == "typescript" else self.language),
                          '\n'.join(f"({kind}) @{group}" for group, kinds in [("import", imports), ("definition", definitions), ("call", calls)] for kind in kinds))
            captures = QueryCursor(query).captures(tree.root_node)
        except (ImportError, LookupError, ValueError, KeyError):
            return []
        claims = []
        for group, nodes in captures.items():
            for n in sorted(nodes, key=lambda n: n.start_byte):
                details = {}
                if group == "import":
                    source = n.child_by_field_name("source") or n.child_by_field_name("path")
                    if source is None:
                        source = next((c for c in walk(n) if c.type in {"string", "string_literal", "interpreted_string_literal", "system_lib_string", "scoped_identifier"}), n)
                    value = text(source).strip('"\'<>')
                    if self.language == "java": value = text(n).removeprefix("import ").removeprefix("static ").rstrip(';').strip()
                    if self.language == "rust": value = text(n).removeprefix("use ").rstrip(';')
                    kind = "dependency"
                elif group == "definition":
                    name = n.child_by_field_name("name") or n.child_by_field_name("declarator") or n.child_by_field_name("pattern")
                    value = text(name)
                    if not value: continue
                    kind = "symbol"
                else:
                    func = n.child_by_field_name("function") or n.child_by_field_name("name") or n.child_by_field_name("macro") or n.child_by_field_name("type")
                    value = text(func)
                    if self.language == "java" and n.child_by_field_name("object"):
                        value = text(n.child_by_field_name("object")) + '.' + value
                    if not value: continue
                    args = n.child_by_field_name("arguments")
                    details = {"positional_count": len(args.named_children) if args else 0}
                    kind = "api"
                claims.append(Claim(claim_type=kind, claim_text=value, source_range=span(n), location=f"line {n.start_point.row + 1}", details=details))
        claims.extend(generic_references(tree.root_node, self.language))
        return claims

    def coverage(self) -> list[AnalyzerCoverage]:
        _, parse = self.parse("x = 1" if self.language == "python" else "")
        return [parse, AnalyzerCoverage(analyzer="symbols", language=self.language, status="available" if self.language == "python" else "partial",
            detail="Python lexical scope and selected catalog APIs" if self.language == "python" else "AST claims and selected catalog APIs; type/build context unavailable", version="2026.1")]



def generic_references(root, language):
    """Resolve lexical names where AST fields are conclusive; missing context stays uncertain."""
    scopes = {'function_declaration', 'function_expression', 'arrow_function', 'method_definition', 'function_item',
              'function_definition', 'method_declaration', 'constructor_declaration', 'func_literal', 'closure_expression',
              'block', 'statement_block', 'compound_statement', 'class_body'}
    declarations = {'variable_declarator', 'var_spec', 'type_spec', 'function_declaration', 'class_declaration',
                    'method_declaration', 'function_item', 'struct_item', 'let_declaration', 'parameter',
                    'formal_parameter', 'required_parameter', 'optional_parameter', 'parameter_declaration',
                    'function_definition', 'declaration', 'short_var_declaration'}
    identifiers = [n for n in walk(root) if n.type == 'identifier']
    def scope(n):
        current = n.parent
        while current and current.type not in scopes: current = current.parent
        return current or root
    def contains(container, node):
        return container is not None and container.start_byte <= node.start_byte and container.end_byte >= node.end_byte
    bindings = []
    declared_ids = set()
    for node in identifiers:
        current = node.parent
        while current and current.type not in scopes:
            if current.type in declarations:
                target = current.child_by_field_name('name') or current.child_by_field_name('pattern') or current.child_by_field_name('declarator') or current.child_by_field_name('left')
                if contains(target, node):
                    bindings.append((text(node), scope(current), current.type, span(node)))
                    declared_ids.add(node.id)
                    break
            current = current.parent
        parent = node.parent
        if parent and parent.type == 'formal_parameters':
            bindings.append((text(node), scope(parent), 'parameter', span(node)))
            declared_ids.add(node.id)
        if parent and parent.type == 'arrow_function' and contains(parent.child_by_field_name('parameter'), node):
            bindings.append((text(node), parent, 'parameter', span(node)))
            declared_ids.add(node.id)
        # Function/method name belongs to its enclosing scope, not its body.
        parent = node.parent
        if parent and parent.type in scopes and contains(parent.child_by_field_name('name'), node):
            bindings.append((text(node), scope(parent), parent.type, span(node)))
            declared_ids.add(node.id)
    import_kinds = set(NODES[language][0])
    for imported in [n for n in walk(root) if n.type in import_kinds]:
        for ident in walk(imported):
            if ident.type == 'identifier': bindings.append((text(ident), root, 'import', span(ident)))
        if language == 'go':
            source = imported.child_by_field_name('path')
            alias = imported.child_by_field_name('name')
            name = text(alias) or text(source).strip('"').split('/')[-1]
            if name and name not in {'_', '.'}: bindings.append((name, root, 'import', span(imported)))
    claims = []
    for node in identifiers:
        if node.id in declared_ids: continue
        current = node.parent
        ignored = False
        while current:
            if current.type in import_kinds or current.type in {'preproc_include', 'package_clause'}: ignored = True; break
            current = current.parent
        if ignored: continue
        parent = node.parent
        if parent and parent.type in {'member_expression', 'field_expression', 'selector_expression', 'method_invocation', 'field_access'}:
            member = parent.child_by_field_name('property') or parent.child_by_field_name('field') or parent.child_by_field_name('name')
            if member and member.id == node.id: continue
        enclosing = scope(node)
        candidates = [b for b in bindings if b[0] == text(node) and contains(b[1], enclosing)]
        binding = min(candidates, key=lambda b: b[1].end_byte-b[1].start_byte) if candidates else None
        claims.append(Claim(claim_type='reference', claim_text=text(node), location=f'line {node.start_point.row+1}', source_range=span(node),
            details={'lexical_binding': binding[3] if binding else None, 'binding_kind': binding[2] if binding else None}))
    return claims

REGISTRY = {name: LanguageAdapter(name) for name in LANGUAGES}


def get_adapter(language: str) -> LanguageAdapter | None:
    return REGISTRY.get(normalize(language))


def python_claims(code: str) -> list[Claim]:
    try: tree = ast.parse(code)
    except SyntaxError: return []
    claims = []
    def dotted(n):
        if isinstance(n, ast.Name): return n.id
        if isinstance(n, ast.Attribute):
            base = dotted(n.value)
            return base + '.' + n.attr if base else ""
        return ""
    def bindings(node, inherited):
        result = dict(inherited)
        class Collector(ast.NodeVisitor):
            def visit_Import(self, n):
                for a in n.names: result[a.asname or a.name.split('.')[0]] = a.name if a.asname else a.name.split('.')[0]
            def visit_ImportFrom(self, n):
                for a in n.names: result[a.asname or a.name] = f"{n.module}.{a.name}"
            def visit_Name(self, n):
                if isinstance(n.ctx, ast.Store): result[n.id] = None
            def visit_FunctionDef(self, n): result[n.name] = None
            visit_AsyncFunctionDef = visit_FunctionDef
            def visit_ClassDef(self, n): result[n.name] = None
            def visit_Lambda(self, n): pass
        collector = Collector()
        for part in node.body: collector.visit(part)
        if hasattr(node, 'args'):
            args = node.args
            for arg in [*args.posonlyargs, *args.args, *args.kwonlyargs, *([args.vararg] if args.vararg else []), *([args.kwarg] if args.kwarg else [])]: result[arg.arg] = None
        return result
    aliases = [bindings(tree, {})]
    def add(n, kind, value, details=None):
        sr = {"start_line": getattr(n, "lineno", 1), "start_column": getattr(n, "col_offset", 0) + 1,
              "end_line": getattr(n, "end_lineno", 1), "end_column": getattr(n, "end_col_offset", 0) + 1}
        claims.append(Claim(claim_type=kind, claim_text=value, location=f"line {sr['start_line']}", source_range=sr, details=details or {}))
    class Visitor(ast.NodeVisitor):
        def visit_Import(self, n):
            for a in n.names: add(n, 'dependency', a.name)
        def visit_ImportFrom(self, n):
            add(n, 'dependency', ('.' * n.level) + (n.module or ''))
            for a in n.names:
                if a.name != '*': add(n, 'api', f"{n.module}.{a.name}", {'imported_member': True, 'catalog_candidate': not n.level})
        def scope(self, n):
            add(n, 'symbol', n.name)
            for part in getattr(n, 'decorator_list', []): self.visit(part)
            if hasattr(n, 'args'):
                for part in [*n.args.defaults, *[d for d in n.args.kw_defaults if d]]: self.visit(part)
                for arg in [*n.args.posonlyargs, *n.args.args, *n.args.kwonlyargs, *([n.args.vararg] if n.args.vararg else []), *([n.args.kwarg] if n.args.kwarg else [])]:
                    if arg.annotation: self.visit(arg.annotation)
                if n.returns: self.visit(n.returns)
            for part in getattr(n, 'bases', []): self.visit(part)
            aliases.append(bindings(n, aliases[-1]))
            for part in n.body: self.visit(part)
            aliases.pop()
        def visit_FunctionDef(self, n): self.scope(n)
        visit_AsyncFunctionDef = visit_FunctionDef
        def visit_ClassDef(self, n): self.scope(n)
        def visit_Call(self, n):
            name = dotted(n.func)
            if name:
                root, *rest = name.split('.')
                alias = aliases[-1].get(root)
                add(n, 'api', name, {'resolved': '.'.join([alias or root, *rest]), 'catalog_candidate': bool(alias),
                    'root_shadowed': root in aliases[-1], 'positional_count': len(n.args), 'keywords': [k.arg for k in n.keywords if k.arg],
                    'dynamic_arguments': any(isinstance(a, ast.Starred) for a in n.args) or any(k.arg is None for k in n.keywords)})
            self.generic_visit(n)
        def visit_Name(self, n):
            if isinstance(n.ctx, ast.Load): add(n, 'reference', n.id)
    Visitor().visit(tree)
    seen = set()
    return [c for c in claims if not ((c.claim_type, c.claim_text, c.location) in seen or seen.add((c.claim_type, c.claim_text, c.location)))]
