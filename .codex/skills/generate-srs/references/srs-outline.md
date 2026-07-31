# Concise SRS Outline

Use this outline as the default for SRS generation.

## 1. Project Overview

Include:

- Project Title
- Problem Statement
- Objectives
- Scope

Write the problem statement as 1-3 paragraphs. List 3-6 objectives. Define scope with "in scope" and, when useful, "out of scope".

## 2. Requirements Analysis

Include:

- Functional Requirements
- Non-functional Requirements
- Stakeholders

Functional requirements:

- Group by module or workflow.
- Use IDs such as `FR-1`, `FR-1.1`, `FR-1.2`.
- Use "The system shall..." or actor-specific "Users shall...".
- Keep each item testable.

Non-functional requirements:

Use a table:

| ID | Category | Requirement |
| --- | --- | --- |
| NFR-1 | Performance | The system shall ... |

Recommended categories: Performance, Security, Usability, Reliability, Availability, Scalability, Maintainability, Compatibility, Privacy, Accessibility.

Stakeholders:

Use a short table:

| Stakeholder | Role / Interest |
| --- | --- |

## 3. System Modeling

Include:

- Use Case Diagram and Descriptions
- Activity Diagram

For use cases:

- Provide one Mermaid use case-style diagram when possible.
- Add a table with use case ID, actor, goal, precondition, main flow, and outcome.
- Keep descriptions concise. Use 4-8 primary use cases.

For activity diagrams:

- Model the most central workflow, not every workflow.
- Use clear start, decision, success, and failure paths.

## 4. Data & Information Modeling

Choose based on project type:

- Traditional software: ER Diagram or Database Schema.
- AI-based software: Dataset Description. Add database schema too if the project stores users, sessions, generated outputs, files, or transactions.

Database schema table:

| Table | Purpose | Key Fields |
| --- | --- | --- |

Dataset description table:

| Dataset / Source | Data Type | Purpose | Preprocessing | Privacy / Risk |
| --- | --- | --- | --- | --- |

## 7. AI Engineering Design

Include only when applicable.

Required subsections:

- AI Pipeline
- Model Selection
- Prompt Design

Recommended additions when relevant:

- Retrieval-Augmented Generation (RAG)
- Evaluation / validation method
- Fallback or error handling
- Privacy and safety controls

Model selection table:

| Component | Candidate / Choice | Reason |
| --- | --- | --- |

Prompt design table:

| Prompt / Agent | Inputs | Expected Output | Constraints |
| --- | --- | --- | --- |

## Length Target

Aim for a concise document that would fit within about 30 pages:

- Project Overview: 2-4 pages
- Requirements Analysis: 8-10 pages
- System Modeling: 6-8 pages
- Data & Information Modeling: 4-6 pages
- AI Engineering Design: 4-6 pages when applicable
