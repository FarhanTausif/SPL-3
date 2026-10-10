# Reference formatting and DOCX construction

## Authority and measured properties

These properties were read from the actual OOXML in `1432_Final_report_spl3_v2.docx`, not inferred from the rubric image. The image supplies content requirements; its Times-like typeface is not the Word report's body font.

| Element | Reference properties |
| --- | --- |
| Page | US Letter, portrait, 8.5 × 11 inches (`12240 × 15840` twips) |
| Margins | 1 inch on all sides (`1440` twips); header/footer distance 0.5 inch (`720` twips) |
| Usable width | 6.5 inches (`9360` twips) |
| Default text | Arial, 11 pt; English; left aligned |
| Default line spacing | 1.15 (`276` with `lineRule=auto`) |
| Body paragraphs | Common direct spacing: 12 pt before and after (`240` twips), inherited 1.15 line spacing |
| Heading 1 | Native `Heading1`, Arial 20 pt, regular; style before 20 pt/after 6 pt; later chapter paragraphs override after to 4 pt and start a new page |
| First chapter title | Direct bold 23 pt override; before 24 pt; preserve the existing template paragraph |
| Heading 2 | Native `Heading2`, 16 pt regular; style before 18 pt/after 6 pt; many later paragraphs override before to 14 pt |
| Early chapter 1 Heading 2 | Several direct 17 pt overrides with 4 pt after; do not silently equate direct formatting with the base style |
| Heading 3 | Native `Heading3`, 14 pt, style color `434343`; before 16 pt/after 4 pt; some source paragraphs override color to black |
| Cover | Centered text; “Final Report,” course, and submission/supervisor labels 15 pt (labels bold); project title 16 pt; names/ID/institution 13 pt; date 12 pt |
| Contents title | “Contents,” 21 pt; unnumbered and outside Heading 1 |
| Tables | Black single borders, 1 pt (`sz=8` eighth-points), left aligned; fixed layout; bold centered headings; common cell padding 5 pt (`100` twips); common cell paragraphs use 12 pt before/after and single line spacing |
| Lists | Real Word numbering/bullets; common left indent 0.5 inch and hanging indent 0.25 inch |
| Figure captions | Plain Arial body-size text, generally centered, `Figure-N: Description`; source uses space padding inconsistently—use actual alignment instead |
| Code | Some runs use Roboto Mono, dark gray, often 10 pt; keep technical snippets short and editable |
| Header/footer | Empty header; body footer has a real `PAGE` field, left aligned |

The source's style definitions and direct overrides are inconsistent in places. The template preserves its first chapter's distinctive heading and uses the later chapters' normal heading treatment for chapters 2–7. Prefer these measured properties over generic academic presets such as Times New Roman 12 pt, A4, 1.5 spacing, or justified body text.

## Bundled template

`../assets/report-template.docx` retains original style definitions, numbering, theme, font assets, cover logos/layout, and empty header/page footer. It removes old project body text, diagrams/screenshots, links, bookmarks, and TOC entries. It provides:

- Cover placeholders: `[PROJECT_TITLE]`, `[COURSE]`, `[STUDENT_NAME]`, `[STUDENT_ID]`, `[SUPERVISOR_NAME]`, `[SUPERVISOR_DESIGNATION]`, `[INSTITUTE]`, `[UNIVERSITY]`, `[SUBMISSION_DATE]`.
- A `TOC \\o "1-3" \\h \\z \\u` field with no invented cached page numbers.
- Exactly seven numbered Heading 1 chapter paragraphs and `[WRITE_CHAPTER_1]` through `[WRITE_CHAPTER_7]` body insertion markers.
- A `ReportBody` paragraph style carrying the source's usual body spacing. Use this for newly inserted narrative paragraphs; source `Normal` alone has no 12 pt before/after spacing.

The two inherited cover logos belong to the reference institution. Keep them only if appropriate for the report's confirmed institution; otherwise replace/remove them without substituting invented logos. The template omits the source's intentional blank page and starts body numbering at 3 after the cover and contents. Recalculate the body start when the contents spans more pages, or adopt a user-requested numbering convention. Do not blindly retain the source's start value of 4.

## Population procedure

Load the template with `python-docx.Document(template_path)`. Replace text at the run level to preserve cover direct formatting. Replace marker paragraphs with content in place, before the next chapter; appending all content at the end gives the wrong chapter order. Useful insertion patterns are `Paragraph.insert_paragraph_before()` for text and moving a newly created table's XML with `marker._p.addprevious(table._tbl)` before deleting the marker.

Assign new body paragraphs `ReportBody`, subsections `Heading 2` / `Heading 3`, and visibly number titles once. The source headings contain literal numbering, so do not attach another automatic numbering system that doubles the numbers. Set direct chapter page breaks using `paragraph_format.page_break_before` while retaining the first chapter's cover/section transition. For early chapter 1 subsections use the documented 17 pt overrides when matching that treatment.

Use actual paragraph spacing/alignment rather than blank paragraphs or repeated spaces for new content. Keep headings with the following paragraph; this is a sensible pagination correction to source paragraphs that disable `keepNext`. Preserve the reference's appearance while avoiding accidental orphans.

### Tables

Using a style name alone does not reproduce the source tables: many borders, widths, margins, and paragraph settings are direct OOXML formatting. Apply `w:tblBorders`/`w:tcBorders` single black 1 pt borders and `w:tcMar` 100-twip padding. Use integer widths summing to at most 9360 twips. Set fixed layout and meaningful column widths, bold centered header text, and readable body alignment. Repeat header rows with `w:tblHeader`; avoid splitting short case rows with `w:cantSplit`, but allow genuinely long content to paginate or restructure it. Do not squeeze nine test-case columns into unreadable text.

### Figures and screenshots

Use centered inline images that preserve aspect ratio and fit within 6.5 inches. Scale to the available page height as well as width. Crop incidental browser chrome only when it does not remove relevant context. Keep text inside diagrams readable at print scale. Add numbered captions and mention each figure in the surrounding narrative. Treat table captions consistently when added. Embed rendered PNGs at adequate resolution or a supported vector format; diagrams must be present in the DOCX, not only as links or fenced source.

### TOC and page fields

Retain native heading styles so the TOC can be regenerated after content changes. Set `w:updateFields` true in `word/settings.xml`; this requests an update but does not itself calculate fields. With python-docx, preserve existing section header/footer references and inspect `w:pgNumType` when changing numbering. Recalculate the first body page from rendered front matter and then rerender if needed.

Word: select all (`Ctrl+A`), update fields (`F9`), and choose to update the entire contents table. LibreOffice can refresh document indexes and fields using its document API when available; a headless PDF export alone is not proof that the TOC was updated. Inspect the exported contents and footer numbering. If refreshing is unavailable, deliver the DOCX with a clear field-update limitation rather than static guessed numbers.

For a temporary visual preview, use an isolated LibreOffice profile and output directory, for example:

```bash
libreoffice -env:UserInstallation=file:///tmp/write-report-lo --headless --convert-to pdf --outdir /tmp/write-report-preview path/to/report.docx
pdftoppm -f 1 -l 2 -scale-to 1400 -png /tmp/write-report-preview/report.pdf /tmp/write-report-preview/front
```

Inspect the resulting images with an available image viewer. Follow environment permission requirements if rendering is blocked. Inspect additional chapter/table/figure pages beyond the first two before claiming a final document has been visually validated.
