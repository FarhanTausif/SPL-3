---
name: dehalu-verification
description: Build or modify DeHalu hallucination detection and mitigation logic. Use when working on claim extraction, Tree-sitter/AST parsing, Semgrep/SAST rules, symbol indexing, package/API validation, MiHN/MaHR/TR-S metrics, entropy/log-prob correlation, LLM-as-a-Judge pool, judge consensus, Chain-of-Verification, policy gateway, repair prompts, retry control, or verification tests.
---

# DeHalu Verification

## Source of Truth

Read `SRS/DeHalu_SRS.md` sections `2.2`, `2.3`, `2.5`, `3.5`, `3.7`, and `5`. Read `SRS/High-Level-Design.md` for the full ASCII phase overview.

## Detection Responsibility

| Category | Error Type | Primary Detector |
| --- | --- | --- |
| Syntactic | Syntax violation | Tree-sitter or language-specific AST parser |
| Syntactic | Incomplete code generation | AST parser plus static heuristics |
| Runtime execution | API knowledge conflict | Symbol indexer plus package/API metadata |
| Runtime execution | Invalid reference errors | Symbol indexer plus static reference analysis |
| Functional correctness | Incorrect logical flow | Judge pool with functional logic rubric |
| Functional correctness | Requirement deviation | Judge pool with requirement-alignment rubric |
| Code quality | Resource mishandling | Semgrep/static rules plus judge review |
| Code quality | Security vulnerability | Semgrep/static rules plus judge review |
| Code quality | Code smell | Static rules, TR-S, and judge review |

## Verification Pipeline

1. Extract claims: imports, packages, APIs, parameters, symbols, functions/classes, runtime assumptions, behavioral claims.
2. Parse source without execution.
3. Run static rules for unsafe constructs, resource misuse, security patterns, and quality issues.
4. Resolve packages, imports, APIs, and references through language-specific symbol indexers with a generic fallback.
5. Compute metrics:
   - MiHN: count of invalid or unsupported micro-level claims.
   - MaHR: proportion of hallucinated claims.
   - TR-S: repetition or degeneration score.
   - Entropy/uncertainty score when provider data exists.
   - hallucination risk score for policy comparison.
6. Run judge pool:
   - Requirement judge.
   - Functional logic judge.
   - Quality/safety judge.
7. Aggregate judge consensus.
8. Run CoVe against static/tool evidence.
9. Apply policy: accept, warn, repair, reject.
10. On repair, constrain the repair prompt with evidence-backed facts and re-run verification.

## Policy Rules

- Static blocking failures outrank judge confidence.
- Unverifiable package/API/symbol claims become `uncertain`, not accepted.
- Repair must not introduce unsupported dependencies.
- Repaired code must pass claim extraction and static verification again.
- Stop repair when `max_retry` is reached.

## Test Cases

Cover at least:

- Fake package import.
- Real package with invented API.
- Undefined helper or variable.
- Syntax error or incomplete code block.
- Requirement deviation.
- Repeated/degenerated code.
- Unsafe file, shell, network, or credential operation.
- Repair that improves metrics.
- Repair that fails and reaches retry limit.
