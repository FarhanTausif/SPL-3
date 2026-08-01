---
name: dehalu-database
description: Build or modify DeHalu database and persistence features. Use when working on SQLAlchemy models, Alembic migrations, repositories, ERD/schema changes, run history, evidence storage, sessions without auth, generated outputs, claims, static findings, metrics, judge pool results, judge consensus, CoVe results, policy decisions, or persistence tests.
---

# DeHalu Database

## Source of Truth

Read `SRS/DeHalu_SRS.md` section `4. Data and Information Modeling` before schema work. Read `SRS/High-Level-Design.md` when changes affect workflow persistence.

## Current Conceptual Schema

Use this SRS-level model unless the user asks to change it:

| Table | Key Fields |
| --- | --- |
| sessions | id (PK), created_at, last_active |
| runs | id (PK), session_id (FK, nullable), prompt, inferred_language, model_name, status, max_retry, created_at, completed_at |
| generated_outputs | id (PK), run_id (FK), attempt_no, code, explanation, provider, entropy_summary, logprob_summary |
| claims | id (PK), output_id (FK), claim_type, claim_text, location, status |
| static_findings | id (PK), output_id (FK), rule_id, severity, message, location, evidence_source |
| metric_results | id (PK), output_id (FK), mihn, mahr, tr_s, entropy_score, hallucination_risk_score |
| judge_results | id (PK), output_id (FK), judge_name, judge_model, verdict, score, rubric_json, explanation, created_at |
| judge_consensus | id (PK), output_id (FK), final_verdict, average_score, agreement_level, summary |
| cove_results | id (PK), output_id (FK), claim_id (FK), verdict, evidence, confidence |
| policy_decisions | id (PK), run_id (FK), output_id (FK), decision, reason, created_at |

Do not add `users.name`, `users.email`, or role-based auth fields unless the user explicitly adds authentication to the scope.

## Relationship Rules

- One session groups many runs.
- One run produces many generated outputs.
- `attempt_no` identifies initial output and repair attempts.
- One generated output has many claims and static findings.
- One generated output has one metrics summary.
- One generated output has many individual judge results and one judge consensus.
- One claim can have many CoVe results.
- Policy decisions attach to both run and output.

## Persistence Rules

- Store evidence as structured data where possible, not only prose.
- Preserve source traceability: output -> claim/finding/metric/judge/CoVe/policy.
- Keep nullable session support for no-auth usage.
- Use JSON columns only for structured payloads that vary by provider/rubric/analyzer.
- Do not store secrets or provider credentials in run records.

## Validation

For schema changes, add or update migrations and repository tests. Verify:

- Initial run with one output.
- Repair run with multiple outputs and increasing `attempt_no`.
- Multiple judge results plus one consensus.
- CoVe results linked to claims.
- Policy decisions linked to the correct output attempt.
