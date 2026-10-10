# Seven-chapter coverage

The chapter titles and order are fixed by the user. Adapt the following default subsections to the evidence without adding top-level chapters.

## 1. Project Overview

- 1.1 Project Title: name, concise description, verified public repository URL when available.
- 1.2 Problem Statement: concrete problem, affected users, motivation.
- 1.3 Objectives: assessable goals to revisit in the conclusion.
- 1.4 Scope: implemented boundaries and proposed/out-of-scope work.
- 1.5 Deliverables: actual software, documentation, delivered artifacts.

## 2. Requirement Analysis

- 2.1 Stakeholders and Users: roles, needs, interactions.
- 2.2 Functional Requirements: grouped requirements with stable IDs, obligations expressed with “shall,” source/priority where supported.
- 2.3 Non-Functional Requirements: ID, category, requirement, measurable acceptance condition when specified. Label proposed thresholds.
- 2.4 Use Cases and System Behavior: actors, use-case diagram, workflows/activity diagrams, preconditions, main/alternative flows, postconditions.
- 2.5 Constraints and Assumptions: environment, dependencies, scope constraints, uncertainties.

## 3. Component Level Design

Both **high-level design of the whole system** and **high-level design of each major component** are required. The rubric image also requires domain design classes, persistent data sources and their classes, behavioral representations, deployment diagrams, and consideration of alternatives/refinement.

- 3.1 Overall System Design: boundary, architecture diagram, components, external services, main data/control flow, and trust/process boundaries where relevant.
- 3.2 Component-wise High-Level Design: a `3.2.x` subsection for each actual major component. Explain purpose, responsibilities, inputs/outputs, collaborators, interface contracts, internal high-level workflow, state/data owned, failure handling, and a diagram where useful. Use actual repository names. For DeHalu this may cover prompt intake/UI, API/orchestrator, generation provider, static verification, judges/consensus, CoVe, policy/repair, streaming, and persistence; include only components supported by evidence.
- 3.3 Domain and Design Classes: classes corresponding to the problem domain, responsibilities and relationships in a class diagram/table. Distinguish implemented classes from conceptual entities.
- 3.4 Persistent Data Sources: databases and files, ER diagram and concise schema, mapping to models/repositories/owning components. Include lifecycle/retention only when known.
- 3.5 Behavioral Design: sequence/activity/state diagrams for principal workflows and interactions, including failure/retry paths. Explain diagrams and align them with contracts and transitions.
- 3.6 Deployment Design: clients, processes/services, storage, providers, connections, supported environments in a deployment diagram. Separate actual deployment from proposed hosting.
- 3.7 Design Decisions and Alternatives: material choices, tradeoffs, rejected alternatives, and refinements supported by evidence. Label recommendations as proposed rather than inventing historical decisions.

For AI projects, document actual pipeline stages, models, prompts, verification/repair policy, and evidence boundaries within relevant component subsections. Do not create a separate AI Engineering chapter.

## 4. Interface Design

The rubric requires interface objects/actions, events that change interface state, and depictions of states as they appear to the end user.

- 4.1 Users, Tasks, and Navigation: principal tasks/navigation grounded in requirements.
- 4.2 Interface Objects and Actions: screen/object, purpose, action, validation, visible feedback.
- 4.3 Events and State Transitions: current state, user/system event, next state, feedback. Cover initial, loading/progress, success, empty, validation/error, recovery where implemented.
- 4.4 Interface Screens: captioned screenshots of meaningful actual states, explaining controls and behavior. Clearly distinguish wireframes from implemented screens.
- 4.5 Usability and Accessibility: implemented responsiveness, readability, keyboard/assistive support, or proposed improvements; avoid unsupported compliance claims.

## 5. Testing

The rubric explicitly requires testing approach/strategy, item pass/fail criteria, risks/contingencies, and test cases with detailed outcomes.

- 5.1 Testing Approach and Strategy: unit, integration, system/UI, other relevant testing; scope, environment/configuration, tools, fixtures, evidence provenance. Distinguish fake-provider runs from live-provider validation.
- 5.2 Item Pass/Fail Criteria: requirement/component IDs and observable outcomes; entry/exit criteria when useful.
- 5.3 Test Cases with Detailed Outcomes: ID, linked requirement/component, preconditions/data, steps, expected result, actual result, status, evidence. Split wide tables or put detailed steps under case headings to keep them readable.
- 5.4 Results and Defect Analysis: observed outcomes, failure causes, fixes/retests, limitations, reproducible commands. Unexecuted cases must say “Not run” or “Planned”; absence of a failure is not a recorded pass.
- 5.5 Risks and Contingencies: risk, testing impact, mitigation, fallback, residual limitation. Include provider availability, nondeterminism, fixture coverage, integration/environment issues when relevant.

## 6. User Manual

- 6.1 System Requirements and Prerequisites.
- 6.2 Installation and Setup: verified repository/distribution URL, dependency/configuration/migration/start commands, installer if one actually exists. Do not publish a repository or create an installer merely to satisfy the rubric.
- 6.3 Starting the Application and Checking Readiness.
- 6.4 Main User Workflows: numbered tasks, real UI labels, inputs, expected outputs, screenshots. Explain result/status/evidence interpretation for DeHalu.
- 6.5 History/Export/Settings: only supported capabilities.
- 6.6 Troubleshooting and Recovery: symptom, probable cause, supported action.

Separate user steps from contributor development instructions. Describe authentication only if it exists; session-based behavior must not become an invented sign-in feature.

## 7. Conclusion

Revisit objectives using demonstrated functionality and test evidence. Summarize contributions, actual limitations, and prioritized future work within this chapter. Do not claim all objectives were achieved unless evidence supports it.

## Rubric deliverables

The attached image mentions about 50–60 pages, a user manual, a publicly accessible version-controlled repository URL, and an installer if applicable. Include the manual as chapter 6, the verified URL in chapters 1/6, and installer instructions only when applicable. The user's seven-chapter scope overrides the reference's additional chapters.
