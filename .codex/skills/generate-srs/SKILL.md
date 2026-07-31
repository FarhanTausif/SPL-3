---
name: generate-srs
description: Generate concise academic Software Requirements Specification (SRS) documents for software engineering projects. Use when Codex is asked to create, draft, improve, or structure an SRS, software requirement analysis document, requirements report, use case/activity/ER modeling section, database schema section, dataset description, or AI engineering design section for a project, especially SPL or university-style reports.
---

# Generate SRS

## Overview

Use this skill to produce a concise SRS document modeled after the supplied SPL technical report style: numbered sections, clear requirement IDs, stakeholder-aware requirements, diagram-ready modeling, and optional AI engineering design.

Prioritize the user's requested structure and keep the output within about 30 pages unless they ask for a longer report.

## Workflow

1. Gather project facts from the prompt, repository, proposal, README, existing docs, or supplied files.
2. If key facts are missing, make conservative assumptions and label them as assumptions rather than blocking.
3. Follow the required SRS outline in `references/srs-outline.md`.
4. Use concise academic prose, numbered requirement IDs, tables where they improve scanning, and diagram-ready Mermaid blocks when drawing actual images is not requested.
5. For AI-based projects, include AI Pipeline, Model Selection, and Prompt Design. For non-AI projects, omit or mark the AI section as not applicable.
6. End with a short completeness check that lists any assumptions, missing inputs, or sections intentionally omitted.

## Document Style

Use the source report's conventions:

- Start with a clear project title and one-paragraph overview.
- Write requirements with stable IDs such as `FR-1.1`, `FR-2.1`, and `NFR-1`.
- Group functional requirements by module, actor, or major workflow.
- Express requirements with "shall" for system obligations.
- Present non-functional requirements as a table with `ID`, `Category`, and `Requirement`.
- Include stakeholders near requirements analysis.
- Describe diagrams briefly before or after each diagram.
- Use concise tables for database schema, dataset descriptions, and model selection.

Avoid padding sections such as literature review, implementation details, testing, deployment, or user manual unless the user explicitly asks for a full technical report rather than SRS.

## Reference Files

- Read `references/srs-outline.md` before drafting any SRS.
- Read `references/writing-rules.md` when deciding tone, numbering, concision, and AI/non-AI handling.
- Read `references/diagram-templates.md` when the SRS needs use case, activity, ER, database schema, or AI pipeline diagrams.

## Output Rules

- Prefer Markdown unless the user asks for LaTeX, DOCX, PDF, or another format.
- Keep headings exactly aligned with the user's requested sections unless they ask for a different standard.
- Include Mermaid diagrams in fenced `mermaid` blocks when possible.
- Keep diagrams readable: 3-6 actors/entities per diagram is usually enough for a concise SRS.
- Do not invent implementation-level endpoints, test counts, libraries, model names, or database fields unless they are provided or clearly implied. Mark uncertain items as proposed.
- For AI projects, document safety/quality concerns such as hallucination risk, data privacy, evaluation, fallback behavior, or prompt constraints when relevant.
