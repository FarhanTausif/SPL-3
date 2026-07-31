# SRS Writing Rules

## Requirements

Good requirements are:

- Atomic: one behavior or constraint per item.
- Testable: a reviewer can verify whether it is satisfied.
- Unambiguous: avoid vague terms such as fast, user-friendly, robust, or modern unless quantified.
- Traceable: use stable IDs.

Functional requirement pattern:

`FR-<module>.<number>: <Actor or system> shall <observable capability or behavior>.`

Examples:

- `FR-1.1: Users shall register using email and password verification.`
- `FR-2.3: The system shall store submitted profile information and allow users to update it.`
- `FR-3.2: The system shall generate a personalized recommendation based on the user's submitted data.`

Non-functional requirement pattern:

`NFR-<number>: The system shall <quality constraint, metric, or design quality>.`

Prefer concrete measures:

- Response time threshold
- Supported screen sizes or browsers
- Authentication and authorization rule
- Data retention or privacy constraint
- Availability or recovery expectation

## Concision

- Use paragraphs for problem context and scope.
- Use tables for stakeholders, non-functional requirements, database schema, datasets, model selection, and prompt design.
- Use bullets for objectives and grouped functional requirements.
- Avoid long explanations of common software engineering terms.
- Avoid implementation details unless they affect requirements or system modeling.

## Handling Missing Information

If the user does not provide enough detail:

- Infer common project actors from the domain.
- Use "Proposed" in schema/model choices when uncertain.
- Add an "Assumptions" note at the end.
- Do not ask follow-up questions unless a missing fact changes the entire document.

## Academic Report Tone

Use formal but direct language. Prefer:

- "The system shall..."
- "The platform provides..."
- "The proposed solution addresses..."
- "The primary stakeholders are..."

Avoid:

- Marketing copy
- Overly broad claims
- Casual phrasing
- Excessive implementation code or API endpoint lists

## AI-Based Project Guidance

For AI systems, include requirements and design points for:

- Input collection and validation
- Data preprocessing
- Model or provider selection
- Prompt construction and output schema
- Retrieval or knowledge base, if used
- Evaluation and feedback
- Human review or fallback, if high risk
- Privacy, consent, and data minimization
- Hallucination or unsafe-output mitigation

Use "model selection" to justify tradeoffs such as accuracy, cost, latency, availability, privacy, explainability, and integration complexity.

Use "prompt design" to document prompt purpose, input variables, expected output, constraints, and guardrails.
