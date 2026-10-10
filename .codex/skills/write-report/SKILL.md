---
name: write-report
description: Generate or revise an academic SPL3 report as a DOCX, preserving 1440_SPL3_Final_Report.docx formatting and applying supervisor guidance on structure, figures, section introductions, and citations. Use for full project reports, not standalone SRS documents.
---

# Write Report

Produce a finished, editable Word document grounded in the project's actual artifacts. The user-edited `1440_SPL3_Final_Report.docx` is the primary formatting authority and revision base. Preserve its fonts and formatting, including direct paragraph/run overrides. Its project narrative is draft material to reconcile with implementation evidence; an older student's report supplies formatting only.

When asked to update this skill, update its instructions and relevant supporting resources only. A skill-update request does not authorize editing the report DOCX; wait for the user's report-revision request.

## Required structure

The report has exactly these seven numbered chapters, in this order and with these titles:

1. Project Title
2. Requirements Analysis
3. Component Level Design
4. Interface Design
5. Testing
6. User Manual
7. Conclusion

Keep the existing cover, Table of Contents, and corrected **List of Figures** as unnumbered front matter. Chapter 1 contains the project title only before **1.1 Abstract**, followed by **1.2 Project Overview**. Do not retain the old `1.1 Project Title` subsection or a descriptive opening before the abstract. The abstract covers the broad domain (SE4AI/AI4SE as applicable, hallucination detection and mitigation, and CodeLLMs), rationale, problem statement, methodology, and evidenced achievements. Merge the current Objectives and Scope and Evolution into Project Overview; retain useful deliverables and evidence context there without duplicating the abstract.

Add an unnumbered **References** section after chapter 7, with bracketed numeric citations and entries matching the proposal's citation structure. This is back matter, not an eighth chapter. Keep models and AI design in chapters 2 and 3. Do not add other chapters unless the user changes the scope.

After each substantive section heading, provide a concise description of its purpose and content. A chapter or parent section must introduce its actual subsections before the first child heading, explaining their relationship and coverage; state subsection counts only when accurate. Leaf sections need an opening explanation before tables, figures, or lists; existing explanatory prose can satisfy this. The title-only opening of chapter 1 is the explicit exception, and front-matter indexes and References do not need artificial summaries.

Read [references/report-outline.md](references/report-outline.md) for coverage derived from the user's rubric image. Read [references/docx-formatting.md](references/docx-formatting.md) before generating the document.

## Gather and write

- Inspect repository guidance, README/runbook, requirements, design documents, source code, schemas/migrations, tests, screenshots, and supplied project material. For DeHalu, look for `High_Level_Design.md` and `SRS/High-Level-Design.md`, `PROJECT_RUNBOOK.md`, `SRS/`, and the backend/frontend implementation. Respect applicable repository guidance when exploring them.
- Use implementation evidence to describe current behavior. Identify proposed features separately when design documents and code differ. Keep a small source-to-section map while drafting so requirements, components, screens, and tests agree.
- Obtain author, student ID, supervisor, institution, course, and submission date from user-provided facts. If essential cover facts remain unavailable, ask a concise question while drafting the rest. For an explicitly requested draft, use visible placeholders and report them; never reuse the reference student's identity or date.
- Preserve the user's existing cover facts in a revision unless explicitly corrected; do not substitute today's date for the supplied submission date.
- Write concise academic prose with hierarchical numbering (`3.1`, `3.1.1`), requirement IDs, useful tables, diagram explanations, and cross-references. Describe component-level high-level design, including both the whole system and each major component, rather than filling the chapter with source listings.
- The rubric suggests approximately 50–60 pages for the final report. Treat that as a planning target unless the user specifies length; do not pad, inflate typography, or sacrifice evidence to meet it. Confirm the page count only after rendering.
- Do not invent test outcomes, measurements, screenshots, URLs, database entities, model choices, or delivered features. Distinguish executed tests, supplied historical evidence, and planned/not-run cases. Record missing evidence where it belongs and summarize material gaps in the delivery message.

## Build the DOCX

For a revision, work on a copy of `1440_SPL3_Final_Report.docx`, retaining the original. Edit in place within that copy rather than rebuilding from the old template. Preserve style/theme/numbering/font assets, direct formatting, cover layout, section breaks, headers/footers, tables, and media except where the requested content change requires a targeted edit. Clone formatting from equivalent nearby elements for added text. Do not normalize fonts, spacing, alignment, or typography to the older report's defaults.

[assets/report-template.docx](assets/report-template.docx) is a legacy fallback for a new report only when the user-edited DOCX is unavailable. Its Arial formatting and old chapter markers do not represent the updated DeHalu report. The original `Demo_Final_Report_SPL3.docx` is a lower-priority fallback; neither overrides the current user-edited DOCX.

Use an available DOCX library, preferably `python-docx`, to edit the revision copy or populate a fallback template when applicable. Check for an existing environment before installing dependencies. Keep generated scripts and draft artifacts in a task/output directory, not inside the application source. Follow the detailed table, diagram, TOC, and pagination guidance in the formatting reference. A Markdown draft alone does not fulfill a DOCX request.

Use actual screenshots for Interface Design and the User Manual. Render architecture, behavior, deployment, and data diagrams into images before embedding them; do not leave Mermaid source or diagram descriptions in place of figures. Label wireframes or proposed states explicitly if screenshots cannot be obtained. Prefer vector/code-based diagrams for technical figures.

Repair the List of Figures from actual report figures: inventory images and captions, resolve missing/duplicate/skipped numbers, update every in-text figure reference, and generate complete caption entries with linked page fields. Retain existing caption appearance. Do not leave empty entries such as `Figure 1:` or fabricate figures to fill numbering gaps. Read the formatting reference for field and pagination handling.

For citations and bibliography construction, read [references/citations.md](references/citations.md). Inspect `SRS/SPL3-Proposal-1440 with Proposal Presentation Feedback.pdf` and relevant PDFs/Markdown in `Papers/`; verify that each cited source actually supports its attached statement. Cite papers and used websites near the supported material, with full metadata and source URLs in References. Proposal citations are leads, not automatically correct mappings or metadata.

## Verify and deliver

- Reopen the DOCX and verify the seven numbered chapters in order, title-only chapter 1 opening, Abstract/Project Overview coverage, introductions before child sections, continuous hierarchical numbering, resolved placeholders, and table consistency. Keep References unnumbered and separate from the seven chapters. Check for stale contents entries, reference-project material, and unintended comments/media.
- Check a one-to-one mapping between actual figures, captions, List of Figures entries, and in-text references. Check that every in-text citation resolves to one bibliography entry, entries are unique and cited, metadata/URLs are supported, and bibliography numbering follows first citation order.
- Compare source/output OOXML formatting and representative elements to detect unintended font, style, geometry, header/footer, table, or image changes. Content and pagination changes are expected; global restyling is not.
- Refresh the TOC, List of Figures, caption/cross-reference fields, and page fields using Word or a working LibreOffice rendering path. Do not fabricate page numbers. If fields cannot be refreshed, disclose the limitation and give the Word update-fields instruction.
- When rendering is available, export a temporary PDF and inspect representative pages: cover, contents, each chapter start, dense tables, diagrams, screenshots, and final page. Correct overflow, cropped images, blank pages, split headers, and unreadable figures. Rendering is required before claiming visual fidelity or a confirmed page count.
- Deliver a clickable link to the `.docx`, state what was generated and verified, and identify any remaining evidence or rendering limitations. Include a PDF only if requested or useful as an additional preview; the editable DOCX remains the primary deliverable.
