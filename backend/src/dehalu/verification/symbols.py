from __future__ import annotations
import ast
import builtins
import symtable
from dehalu.domain.models import Claim, StaticFinding
from dehalu.core.settings import settings
from dehalu.verification.adapters import normalize
from dehalu.verification.catalogs import APIS, COMPLETE_MODULES, VERSION, package_status


def python_references(code: str) -> dict[tuple[str, int], bool | None]:
    """Use Python's symbol tables for nested scopes; inspect syntax without imports."""
    try:
        root = symtable.symtable(code, "snippet.py", "exec")
        tree = ast.parse(code)
    except SyntaxError:
        return {}
    result = {}
    tables = [root]
    def bound(name, table):
        try: symbol = table.lookup(name)
        except KeyError: return False
        return symbol.is_assigned() or symbol.is_imported() or symbol.is_parameter() or symbol.is_namespace()
    def resolve(name):
        if name in vars(builtins): return True
        current = tables[-1]
        try: symbol = current.lookup(name)
        except KeyError: return None
        if symbol.is_global(): return bound(name, root)
        if symbol.is_free(): return any(bound(name, t) for t in reversed(tables[:-1]) if t.get_type() != 'class')
        return bound(name, current)
    class Visitor(ast.NodeVisitor):
        def visit_Name(self, node):
            if isinstance(node.ctx, ast.Load): result[(node.id, node.lineno)] = resolve(node.id)
        def visit_scope(self, node, name):
            # Defaults, bases and decorators resolve in the enclosing scope.
            for part in getattr(node, 'decorator_list', []): self.visit(part)
            if hasattr(node, 'args'):
                for part in [*node.args.defaults, *[d for d in node.args.kw_defaults if d]]: self.visit(part)
                for arg in [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs, *([node.args.vararg] if node.args.vararg else []), *([node.args.kwarg] if node.args.kwarg else [])]:
                    if arg.annotation: self.visit(arg.annotation)
                if node.returns: self.visit(node.returns)
            for part in getattr(node, 'bases', []): self.visit(part)
            child = next((t for t in tables[-1].get_children() if t.get_name() == name and t.get_lineno() == node.lineno), None)
            if child:
                tables.append(child)
                for part in node.body: self.visit(part)
                tables.pop()
        def visit_FunctionDef(self, node): self.visit_scope(node, node.name)
        visit_AsyncFunctionDef = visit_FunctionDef
        def visit_ClassDef(self, node): self.visit_scope(node, node.name)
        def visit_Lambda(self, node):
            # Unsupported nested expression scopes remain uncertain, not falsely undefined.
            for n in ast.walk(node):
                if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load): result[(n.id, n.lineno)] = None
        def visit_ListComp(self, node):
            for n in ast.walk(node):
                if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load): result[(n.id, n.lineno)] = None
        visit_SetComp = visit_ListComp
        visit_DictComp = visit_ListComp
        visit_GeneratorExp = visit_ListComp
    Visitor().visit(tree)
    # Wildcard imports and runtime namespace mutation prevent definite missing-name evidence.
    dynamic = any(isinstance(n, ast.ImportFrom) and any(a.name == '*' for a in n.names) for n in ast.walk(tree))
    if dynamic: return {key: (True if value else None) for key, value in result.items()}
    return result


def validate_symbols(code: str, language: str, claims: list[Claim]) -> list[StaticFinding]:
    language = normalize(language)
    refs = python_references(code) if language == 'python' else {}
    findings = []
    def mark(claim, status, evidence, rule=None):
        claim.status = status
        claim.evidence = evidence
        if rule:
            finding = StaticFinding(rule_id=rule, severity='error' if status == 'unsupported' else 'warning', message=evidence,
                location=claim.location, source_range=claim.source_range, claim_ids=[claim.id], evidence_source=f"Symbol/API catalog {VERSION}")
            claim.evidence_ids.append(finding.id)
            findings.append(finding)
    for c in claims:
        if c.claim_type == 'dependency':
            status, evidence = package_status(language, c.claim_text, settings.package_lookups)
            mark(c, status, evidence, 'symbol-indexer.unresolved-import' if status != 'supported' else None)
        elif c.claim_type == 'symbol':
            mark(c, 'supported', f"Definition present at {c.location}.")
        elif c.claim_type == 'reference':
            present = refs.get((c.claim_text, c.source_range.get('start_line', 0))) if language == 'python' else True if c.details.get('lexical_binding') else None
            if language in {'javascript', 'typescript'} and c.claim_text in {'JSON', 'console', 'Math', 'Number', 'String', 'Boolean', 'Array', 'Object', 'Promise', 'Error', 'Map', 'Set'}:
                present = True
            mark(c, 'supported' if present else 'unsupported' if present is False else 'uncertain',
                 f"Static binding {'found' if present else 'missing' if present is False else 'cannot be resolved'} for {c.claim_text}.",
                 'symbol-indexer.invalid-reference' if present is False else None)
        elif c.claim_type == 'api':
            resolved = c.details.get('resolved', c.claim_text)
            root = c.claim_text.split('.')[0]
            if language == 'python' and not c.details.get('imported_member'):
                present = refs.get((root, c.source_range.get('start_line', 0)))
                if present is False:
                    mark(c, 'unsupported', f"Undefined call target {root}.", 'symbol-indexer.invalid-reference')
                    continue
                if '.' not in resolved and present and root in vars(builtins) and not c.details.get('root_shadowed'):
                    mark(c, 'supported', f"Python builtin {root}; full argument validation not available.")
                    continue
                if '.' not in resolved and present:
                    mark(c, 'uncertain', f"Local target {root} is bound; callability/signature requires further type or semantic evidence.")
                    continue
            catalog_candidate = language != 'python' or c.details.get('catalog_candidate', False)
            if language != 'python':
                root_name = c.claim_text.split('.')[0].split('::')[0]
                same_line = [ref for ref in claims if ref.claim_type == 'reference' and ref.claim_text == root_name and ref.source_range.get('start_line') == c.source_range.get('start_line')]
                if any(ref.details.get('lexical_binding') and ref.details.get('binding_kind') != 'import' for ref in same_line):
                    catalog_candidate = False
                if language == 'go' and not any(dep.claim_type == 'dependency' and dep.claim_text == root_name for dep in claims):
                    catalog_candidate = False
            signature = APIS.get(language, {}).get(resolved) if catalog_candidate else None
            if signature:
                lo, hi, keywords = signature
                count = c.details.get('positional_count', 0)
                if not c.details.get('imported_member') and not c.details.get('dynamic_arguments') and (count < lo or (hi is not None and count > hi) or (keywords is not None and set(c.details.get('keywords', [])) - set(keywords))):
                    mark(c, 'unsupported', f"Arguments conflict with catalog signature for {resolved}.", 'symbol-indexer.api-conflict')
                else: mark(c, 'supported', f"API confirmed by catalog {VERSION}: {resolved}.")
            else:
                module, _, member = resolved.rpartition('.')
                complete = COMPLETE_MODULES.get(language, {}).get(module) if catalog_candidate else None
                if complete is not None and member not in complete:
                    mark(c, 'unsupported', f"{member} is absent from complete {module} API catalog {VERSION}.", 'symbol-indexer.api-conflict')
                else: mark(c, 'uncertain', f"No complete signature/type metadata for {resolved}.")
        elif c.status == 'not_checked':
            mark(c, 'uncertain', 'Claim requires additional semantic or environment evidence.')
    return findings
