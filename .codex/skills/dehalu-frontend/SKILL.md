---
name: dehalu-frontend
description: Build or modify DeHalu frontend features. Use when working on Next.js/React UI for prompt intake, live verification workflow visualization, detection and mitigation diagrams, evidence panels, hallucination metrics, judge-pool results, CoVe findings, policy decisions, repaired code display, responsive layout, or frontend tests.
---

# DeHalu Frontend

## Source of Truth

Before editing UI behavior, read:

- `SRS/DeHalu_SRS.md` for actors, use cases, workflows, evidence fields, and policy outcomes.
- `SRS/High-Level-Design.md` for the current phase overview.
- Existing frontend architecture docs if present.

If implementation files exist, follow the existing component, state, API, and styling conventions.

## Product Shape

Build the actual verification workspace as the first screen, not a marketing page. The UI should support:

- Prompt entry and optional inferred language/framework/runtime display.
- Live workflow visualization from generation through detection, policy, and repair.
- Evidence inspection for claims, static findings, symbol/API validation, metrics, judges, CoVe, and policy.
- Final code display for verified, warned, repaired, or rejected outputs.

## Required Views

- Prompt workspace: prompt input, submit action, optional assumptions/constraints, run status.
- Workflow monitor: phase nodes for normalization, generation, claim extraction, static detection, metric engine, judge pool, consensus, CoVe, policy, repair, retry.
- Evidence panel: stage-level findings with severity, location, source, and claim links.
- Metrics panel: MiHN, MaHR, TR-S, entropy/uncertainty, hallucination risk, before/after repair comparison.
- Judge panel: individual judge verdicts plus consensus verdict, average score, and agreement level.
- Result panel: final code, policy decision, reasons, and repair notes.

## UI Rules

- Keep operational UI dense, readable, and task-focused.
- Use tabs for major evidence groups and compact panels for repeated items.
- Use status badges for stage state and policy outcomes.
- Use icons for actions when available in the project icon library.
- Avoid implying execution-based verification; label the pipeline as execution-free/static-analysis-first.
- Show uncertainty explicitly when a package/API/symbol claim cannot be verified.

## Validation

If frontend exists, run the narrowest relevant checks:

```bash
npm test
npm run lint
```

For workflow or responsive changes, verify key views at desktop and mobile sizes. Ensure text does not overlap in cards, badges, tables, or graph nodes.
