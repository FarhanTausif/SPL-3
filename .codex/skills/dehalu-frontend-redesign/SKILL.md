---
name: dehalu-frontend-redesign
description: Redesign DeHalu frontend experiences into a polished Claude-like AI workspace with streamed code generation, animated workflow progress, evidence tabs, status badges, attempt comparison, diff views, and responsive operational UI.
---

# DeHalu Frontend Redesign

Use this skill when redesigning or extending the DeHalu frontend workspace.

## Visual Direction

- Build the actual verification workspace as the first screen.
- Use shadcn/ui-style components and Tailwind CSS utilities as the default implementation surface.
- Use a modern AI workspace feel inspired by current AI chat products and high-end AI dashboard shots: calm density, readable panels, white focused composer, green/neutral accents, precise status language, and restrained motion.
- Avoid marketing layouts, oversized hero sections, decorative cards, gradient-heavy themes, and nested cards.
- Use `lucide-react` icons for actions and states.
- Keep code and evidence easy to scan for repeated debugging/demo use.
- Prefer modern product typography: strong hierarchy, tight operational copy, readable line heights, and no viewport-scaled font sizes.

## Required Surfaces

- Chat-style prompt composer with auto-growing text area and immediate running state.
- Streamed code output separated by attempt: initial generation and latest/repaired generation.
- Compact horizontal workflow monitor with stage status, progress, and active animation. Avoid long vertical workflow stacks.
- Evidence tabs for claims, static findings, metrics, judges, CoVe, policy, and attempts using shadcn Tabs.
- Diff view comparing attempt 1 with the latest attempt using line-level add/remove highlighting.
- Clarification and uncertain-assumption panels when returned by the backend.
- Syntax-highlighted code and diff panels with editor-like styling.

## Badge Semantics

- Green: `supported`, `pass`, `accept`, `completed`.
- Red: `unsupported`, `fail`, `reject`, `error`.
- Amber: `uncertain`, `warn`, `warning`, `repair`.
- Blue: `needs_clarification`, active/running states.
- Gray: `not_checked`, `pending`, unknown values.

## Interaction Rules

- Do not expose `language_hint` or `max_retry` controls unless explicitly requested.
- Do not show explanatory UI copy that says language/retry policy is inferred.
- Prompt composer should resemble modern ChatGPT-style input: white surface, compact rounded corners, minimal chrome, and a strong send button.
- Keep composer controls minimal; do not add unused plus, mic, audio, or settings buttons until their behavior exists.
- Keep the Run button responsive and show streamed output as soon as backend events arrive.
- Animate progress transitions, but keep motion subtle and non-blocking.
- Preserve the existing non-streaming API as a fallback/debug path.
- Ensure text never overlaps inside badges, cards, tabs, or workflow nodes at mobile and desktop widths.
- Metrics must expose hover/focus tooltips explaining each score.
- Metrics should use a comparison table across all generation/repair attempts, not only latest-attempt metric cards.
- Evidence text outside metrics should render with `react-markdown` or an equivalent Markdown renderer.
- Badges and tab triggers should be compact with low height and restrained radius. Avoid tall pill tags in evidence-heavy surfaces.
- Code tabs must not expand page width; wrap long lines, cap panel width to the parent, and keep internal scrolling inside the editor frame.
- Use responsive grids with `minmax(0, 1fr)`, explicit overflow handling, and horizontal scrolling for dense stage/tab rows.

## Validation

Run:

```bash
npm test
npm run build
```

For major layout work, manually verify desktop and mobile widths, empty states, streaming states, final states, and repair/diff states.
