import pytest
from dehalu.verification.adapters import REGISTRY
from dehalu.verification.claims import extract_claims
from dehalu.verification.symbols import validate_symbols
from dehalu.verification.cove import run_cove
from dehalu.verification.catalogs import package_status

CASES = {
 'python': 'def add(a, b):\n return a+b',
 'javascript': 'import fs from "fs"; function f(x) { return JSON.stringify(x); }',
 'typescript': 'function f(x: number): number { return x; }',
 'java': 'import java.util.List; class X { double f(int x) { return Math.sqrt(x); } }',
 'go': 'package main\nimport "fmt"\nfunc main(){ fmt.Println("hello") }',
 'rust': 'use std::fs; fn main() { std::fs::read_to_string("a"); }',
 'c': '#include <stdio.h>\nint main(){ printf("x"); return 0; }',
 'cpp': '#include <iostream>\nint main(){ return 0; }',
}

@pytest.mark.parametrize('language,code', CASES.items())
def test_all_adapters_parse_and_extract(language, code):
    findings, coverage = REGISTRY[language].parse(code)
    assert coverage.status == 'available'
    assert not findings
    claims = REGISTRY[language].extract(code)
    assert claims and all(c.id and c.source_range for c in claims)

@pytest.mark.parametrize('language', CASES)
def test_malformed_code_has_parser_evidence(language):
    findings, _ = REGISTRY[language].parse('def ??? {{{')
    assert any(f.severity == 'error' for f in findings)


def analyze(code):
    claims = extract_claims(code)
    findings = validate_symbols(code, 'python', claims)
    return claims, findings


def test_python_parameters_aliases_nested_scopes_and_shadowing():
    claims, findings = analyze('import json as j\ndef f(x):\n return j.dumps(x)\n')
    assert not any(f.severity == 'error' for f in findings)
    assert next(c for c in claims if c.claim_text == 'j.dumps').status == 'supported'
    claims, _ = analyze('import json\ndef f(json):\n return json.invented()\n')
    assert next(c for c in claims if c.claim_text == 'json.invented').status == 'uncertain'
    _, findings = analyze('def f():\n local = 1\n return local\nprint(local)')
    assert any('missing' in f.message and f.location == 'line 4' for f in findings)


def test_invented_api_and_invalid_parameters_use_complete_evidence():
    for code in ['import json\njson.invented_api("x")', 'import json\njson.loads("x", invented=True)']:
        claims, findings = analyze(code)
        assert any(f.rule_id == 'symbol-indexer.api-conflict' for f in findings)
        assert any(c.verdict == 'unsupported' and c.evidence_ids for c in run_cove(claims, findings))


def test_registry_absence_and_outage_are_distinct(monkeypatch):
    import httpx
    from dehalu.verification import catalogs
    catalogs._CACHE.clear()
    monkeypatch.setattr(httpx, 'get', lambda *a, **k: httpx.Response(404))
    assert package_status('python', 'unknown_123', True)[0] == 'unsupported'
    def offline(*a, **k): raise httpx.ConnectError('offline')
    monkeypatch.setattr(httpx, 'get', offline)
    assert package_status('python', 'unknown_456', True)[0] == 'uncertain'


def test_standard_namespace_does_not_prove_invented_submodule():
    assert package_status('python', 'json.nonexistent')[0] == 'uncertain'
    assert package_status('java', 'java.util.InventedCollection')[0] == 'uncertain'
    assert package_status('javascript', 'fs/invented')[0] == 'uncertain'


def test_js_lexical_parameters_and_block_bindings():
    code = 'function f(x) { const y=x+1; return y + unknown; }'
    claims = REGISTRY['javascript'].extract(code)
    validate_symbols(code, 'javascript', claims)
    assert all(c.status == 'supported' for c in claims if c.claim_type == 'reference' and c.claim_text in {'x', 'y'})
    assert next(c for c in claims if c.claim_text == 'unknown').status == 'uncertain'


def test_undefined_python_annotation_is_checked():
    claims, findings = analyze('def f(x: InventedType):\n return x')
    assert any(c.claim_text == 'InventedType' and c.status == 'unsupported' for c in claims)


def test_js_standard_global_shadow_does_not_prove_api():
    code = 'function f(JSON) { return JSON.stringify("x"); }'
    claims = REGISTRY['javascript'].extract(code)
    validate_symbols(code, 'javascript', claims)
    assert next(c for c in claims if c.claim_type == 'api').status == 'uncertain'
