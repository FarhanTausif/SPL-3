---
name: dehalu-backend
description: Build or modify DeHalu backend features. Use when working on FastAPI/service-layer code for prompt intake, local CodeLLM generation, run orchestration, judge-pool execution, CoVe, policy decisions, repair loops, API contracts, background workers, or backend tests for the DeHalu static hallucination detection system.
---

# DeHalu Backend

## Source of Truth

Before changing backend behavior, read:

- `SRS/DeHalu_SRS.md` for requirements, hallucination taxonomy, ERD, and policy outcomes.
- `SRS/High-Level-Design.md` for the current phase pipeline.
- `PROJECT_RUNBOOK.md` if present for local commands and runtime notes.

If implementation files exist, inspect the current structure first and follow local patterns. Expected backend stack is Python, FastAPI, SQLAlchemy/Alembic, and provider adapters for local CodeLLMs.

## Architecture Rules

- Preserve the execution-free committed scope: do not add arbitrary code execution as a required verification stage.
- Treat deterministic static evidence as primary for syntax, incomplete code, API conflicts, invalid references, and known unsafe patterns.
- Treat LLM-as-a-Judge pool output as semantic evidence, not absolute proof.
- Support policy outcomes: `accept`, `warn`, `repair`, `reject`.
- Route repaired code back through claim extraction and static verification before returning it.
- Track retry count with output `attempt_no` and a `max_retry` limit at run/config level.

## Backend Workflow

1. Normalize the request: prompt, language/framework/runtime hints, uncertainty flags.
2. Generate code through a local CodeLLM provider adapter and capture metadata, entropy, and log-probability signals when available.
3. Extract checkable claims from code and explanation.
4. Run static analyzers and symbol/API validators through language-specific adapters with a generic fallback.
5. Compute MiHN, MaHR, TR-S, static severity, uncertainty, and hallucination risk metrics.
6. Run judge-pool roles for requirement alignment, functional logic, and quality/safety review.
7. Aggregate judge consensus: final semantic verdict, average score, agreement level.
8. Run CoVe claim checks against static/tool evidence.
9. Apply deterministic policy. On repair, build evidence-backed failure context and re-enter verification after repair.
10. Persist run, outputs, claims, findings, metrics, judge results, consensus, CoVe results, and policy decisions.

## API Expectations

Prefer contract-first changes. Backend responses should expose enough data for the frontend to render:

- Run status, stage status, and timestamps.
- Generated or repaired code.
- Extracted claims and claim statuses.
- Static findings with severity, message, location, and evidence source.
- Metrics including `mihn`, `mahr`, `tr_s`, entropy/uncertainty score, and hallucination risk score.
- Individual judge results and judge consensus.
- CoVe verdicts.
- Policy decision and reasons.

## Validation

Run the narrowest relevant tests first. If backend exists, prefer:

```bash
pytest
```

For API changes, include route/service tests. For policy, metric, claim, judge, CoVe, or repair changes, include unit tests for both clean and hallucinated outputs.
