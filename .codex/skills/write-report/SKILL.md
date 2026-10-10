---
name: write-report
description: Generate or revise an academic project report as a DOCX using the formatting of 1432_Final_report_spl3_v2.docx and the prescribed seven-chapter SPL3 structure. Use for full project reports, not standalone SRS documents.
---

# Write Report

Produce a finished, editable Word document grounded in the project's actual artifacts. Use the supplied report as a formatting reference, never as a source of project facts.

## Required structure

The report has exactly these seven numbered chapters, in this order and with these titles:

1. Project Overview
2. Requirement Analysis
3. Component Level Design
4. Interface Design
5. Testing
6. User Manual
7. Conclusion

Keep the reference's cover and contents as unnumbered front matter. They are not additional report chapters. Do not add an abstract, acknowledgement, literature review, separate System Modeling, Data Modeling, AI Engineering, Implementation, References, or appendix chapter unless the user changes the scope. Put relevant models and AI design under chapters 2 and 3; cite sources near the material they support.

Read [references/report-outline.md](references/report-outline.md) for coverage derived from the user's rubric image. Read [references/docx-formatting.md](references/docx-formatting.md) before generating the document.

## Gather and write

- Inspect repository guidance, README/runbook, requirements, design documents, source code, schemas/migrations, tests, screenshots, and supplied project material. For DeHalu, look for `High_Level_Design.md` and `SRS/High-Level-Design.md`, `PROJECT_RUNBOOK.md`, `SRS/`, and the backend/frontend implementation. Respect applicable repository guidance when exploring them.
- Use implementation evidence to describe current behavior. Identify proposed features separately when design documents and code differ. Keep a small source-to-section map while drafting so requirements, components, screens, and tests agree.
- Obtain author, student ID, supervisor, institution, course, and submission date from user-provided facts. If essential cover facts remain unavailable, ask a concise question while drafting the rest. For an explicitly requested draft, use visible placeholders and report them; never reuse the reference student's identity or date.
- Write concise academic prose with hierarchical numbering (`3.1`, `3.1.1`), requirement IDs, useful tables, diagram explanations, and cross-references. Describe component-level high-level design, including both the whole system and each major component, rather than filling the chapter with source listings.
- The rubric suggests approximately 50–60 pages for the final report. Treat that as a planning target unless the user specifies length; do not pad, inflate typography, or sacrifice evidence to meet it. Confirm the page count only after rendering.
- Do not invent test outcomes, measurements, screenshots, URLs, database entities, model choices, or delivered features. Distinguish executed tests, supplied historical evidence, and planned/not-run cases. Record missing evidence where it belongs and summarize material gaps in the delivery message.

## Build the DOCX

Start from [assets/report-template.docx](assets/report-template.docx), a compact derivative of the reference with its style/theme/numbering/font assets and cover layout, but with project-specific text and body illustrations removed. Replace its placeholders and chapter-body markers. Preserve native Word heading styles, editable text/tables, page geometry, and footer fields. The original `1432_Final_report_spl3_v2.docx`, when present, is the authority for ambiguous formatting details.

Use an available DOCX library, preferably `python-docx`, to populate the template. Check for an existing environment before installing dependencies. Keep generated scripts and draft artifacts in a task/output directory, not inside the application source. Follow the detailed table, diagram, TOC, and pagination guidance in the formatting reference. A Markdown draft alone does not fulfill a DOCX request.

Use actual screenshots for Interface Design and the User Manual. Render architecture, behavior, deployment, and data diagrams into images before embedding them; do not leave Mermaid source or diagram descriptions in place of figures. Label wireframes or proposed states explicitly if screenshots cannot be obtained. Prefer vector/code-based diagrams for technical figures.

## Verify and deliver

- Reopen the DOCX and verify all seven Heading 1 chapters in order, hierarchical subsection numbering, resolved cover/body placeholders, captions/cross-references, table consistency, and absence of reference-project names, old contents entries, comments, and unrelated media.
- Refresh the TOC and page fields using Word or a working LibreOffice rendering path. Do not fabricate page numbers. If fields cannot be refreshed, disclose the limitation and give the Word update-fields instruction.
- When rendering is available, export a temporary PDF and inspect representative pages: cover, contents, each chapter start, dense tables, diagrams, screenshots, and final page. Correct overflow, cropped images, blank pages, split headers, and unreadable figures. Rendering is required before claiming visual fidelity or a confirmed page count.
- Deliver a clickable link to the `.docx`, state what was generated and verified, and identify any remaining evidence or rendering limitations. Include a PDF only if requested or useful as an additional preview; the editable DOCX remains the primary deliverable.
