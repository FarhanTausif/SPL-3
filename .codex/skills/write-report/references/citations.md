# Citations and References

## Sources and convention

Read `SRS/SPL3-Proposal-1440 with Proposal Presentation Feedback.pdf` for its bracketed numeric convention and reference leads. Inspect relevant full PDFs and saved website Markdown in `Papers/` for source content and metadata. Other proposals can supplement these sources but do not override the explicitly supplied feedback proposal.

The proposal uses inline `[1]` citations and numbered entries containing authors, quoted title, venue or arXiv identifier, and year. Follow this structure, adding verified DOI/canonical URLs and publication metadata. Number entries in first-citation order, reuse numbers for repeated sources and list each source once. Do not preserve proposal numbers after changing source order.

Add **References** after chapter 7 as unnumbered back matter and include it in the TOC. Match local typography rather than switching to author–date citations or an unrelated bibliography font.

## Source and claim verification

The proposal's mappings need checking: its Chain-of-Thought bullet cites the taxonomy paper, and its sandbox-execution bullet cites the paper on Chain-of-Thought obscuring hallucination cues. Treat these as leads to inspect, not valid mappings to copy. Verify authors, exact titles, dates, venues, volume/pages and identifiers from paper front matter or authoritative publication records. Filenames and proposal entries alone are insufficient; do not carry unsupported metadata forward.

Useful local source groups:

- Taxonomy, CodeHalu, systematic literature review and empirical static-analysis study for problem/domain and methodology context.
- Chain-of-Verification, Chain-of-Thought elicitation and Chain-of-Thought obscuring hallucination cues for their respective methods and limitations.
- ClarifyGPT and metamorphic-relations paper for clarification or explicitly historical/proposed alternatives. Citations do not establish implementation in DeHalu.
- Saved website articles on LLM-as-a-judge, hallucination detection and monitoring for claims they actually support. Extract each article's own canonical URL; ignore login/tracking/image/profile/share links as article references.

Cite original research for technical claims when available. A saved article's bibliography is a discovery aid, not evidence that every listed source was used. Implementation claims require repository/test evidence. Preserve the supervisor's static-analysis-only scope: sandbox/metamorphic proposals must not become current system behavior.

Extract metadata/content locally first. When metadata or URLs are missing, ambiguous or need verification, consult the publisher, DOI resolver, arXiv abstract page or original website. Verify externally referenced page contents before relying on them. Do not invent publication fields or URLs; disclose unresolved information if it cannot be resolved. Updating this skill does not require preparing a finished bibliography or editing the report.

## Entry patterns

Adapt these patterns to verified metadata; placeholders below are illustrative, not report content:

- Paper: `[n] A. Author et al., "Exact paper title," Venue, vol. ..., no. ..., pp. ..., year. doi: ... . Available: canonical DOI/publisher URL.` Omit fields that do not apply.
- Preprint: `[n] A. Author et al., "Exact paper title," arXiv preprint arXiv:identifier, year. Available: https://arxiv.org/abs/identifier.` Prefer a confirmed published record; include version information when material.
- Website: `[n] Author or organization, "Page title," Site name, publication/update date when stated. [Online]. Available: canonical page URL. [Accessed: actual access date].` Never invent a publication date or substitute the proposal/report date for the access date.

Keep URLs editable and clickable in Word with equivalent local formatting. Cite near supported statements and distinguish a method's origin from empirical effectiveness. Do not claim superiority or live-model performance without evidence.

## Verification

Maintain a compact claim-to-source map while drafting. Check that citations resolve, bibliography entries are cited/unique, numbering follows first use, and metadata/URLs agree with inspected sources. Recheck tables/captions and citations after section moves and chapter 1 merges. Use a relevant bibliography rather than copying every file or link in `Papers/`.
