---
name: dehalu-evaluation
description: Design or update DeHalu evaluation, validation, and academic reporting artifacts. Use when creating benchmark prompts, hallucination test cases, evaluation datasets, metric reports, SRS/design validation sections, experiment tables, result analysis, or final report content for DeHalu's static hallucination detection and mitigation system.
---

# DeHalu Evaluation

## Source of Truth

Read `SRS/DeHalu_SRS.md` and `SRS/High-Level-Design.md` before drafting evaluation artifacts. Use papers in `Papers/` when the user asks for literature-grounded evaluation.

## Evaluation Scope

Evaluate DeHalu against the taxonomy:

- Syntactic hallucinations: syntax violations, incomplete code.
- Runtime execution hallucinations handled statically: API knowledge conflicts, invalid references.
- Functional correctness hallucinations: incorrect logical flow, requirement deviation.
- Code quality hallucinations: resource mishandling, security vulnerability, code smell.

Do not claim exhaustive runtime correctness or full security auditing. State that functional and broad quality results are semantic/rubric-based evidence.

## Case Design

For each case, define:

- Prompt.
- Target language.
- Expected hallucination type.
- Seeded or expected failure signal.
- Static evidence expected.
- Judge-pool responsibility.
- Expected policy outcome: accept, warn, repair, reject.
- Expected metric direction, especially before/after repair.

Prefer compact JSON or table formats that can become tests later.

## Metrics Interpretation

- MiHN counts invalid or unsupported micro-level claims.
- MaHR measures the proportion of hallucinated claims.
- TR-S measures repetition or degeneration.
- Entropy/log-prob signals support uncertainty correlation when available.
- hallucination risk score summarizes evidence for policy and comparison.

Use metrics to compare initial and repaired outputs. Avoid presenting metrics as mathematical proof of correctness.

## Reporting Structure

Use concise academic sections:

1. Evaluation Objective.
2. Dataset or Prompt Set.
3. Hallucination Categories Covered.
4. Evaluation Method.
5. Metrics.
6. Results Table.
7. Error Analysis.
8. Threats to Validity.

## Validation Checks

Ensure the report states:

- Static evidence is primary for syntax/API/reference findings.
- Judge pool handles semantic correctness, requirement deviation, and broad quality review.
- Policy combines static findings, metrics, judge consensus, and CoVe evidence.
- Repair is accepted only after re-verification.
