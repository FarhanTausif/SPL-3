# Diagram Templates

Use Mermaid blocks unless the user requests another diagram format.

## Use Case Diagram

Mermaid does not have native UML use-case syntax in all renderers. Use a readable flowchart approximation:

```mermaid
flowchart LR
    User((User))
    Admin((Admin))
    External((External Service))

    subgraph System[Project System]
        UC1[Register / Sign In]
        UC2[Manage Profile]
        UC3[Submit Request]
        UC4[Generate Output]
        UC5[Review History]
        UC6[Admin Management]
    end

    User --> UC1
    User --> UC2
    User --> UC3
    User --> UC4
    User --> UC5
    Admin --> UC6
    UC4 --> External
```

Use 2-4 actors and 4-8 use cases for concise SRS documents.

## Use Case Description Table

| Use Case ID | Use Case | Primary Actor | Preconditions | Main Flow | Outcome |
| --- | --- | --- | --- | --- | --- |
| UC-1 | Register / Sign In | User | User has access to the application | User submits credentials; system validates; session starts | User is authenticated |

## Activity Diagram

```mermaid
flowchart TD
    Start([Start])
    Input[User provides required information]
    Validate{Input valid?}
    Fix[Show validation message]
    Process[Process request]
    Decision{Successful?}
    Output[Show result and store record]
    Error[Show failure message]
    End([End])

    Start --> Input --> Validate
    Validate -- No --> Fix --> Input
    Validate -- Yes --> Process --> Decision
    Decision -- Yes --> Output --> End
    Decision -- No --> Error --> End
```

## ER Diagram

```mermaid
erDiagram
    USER ||--o{ REQUEST : submits
    USER ||--o{ SESSION : owns
    REQUEST ||--o| RESULT : produces
    ADMIN ||--o{ AUDIT_LOG : reviews

    USER {
        uuid id PK
        string name
        string email
        string role
    }

    REQUEST {
        uuid id PK
        uuid user_id FK
        string status
        datetime created_at
    }

    RESULT {
        uuid id PK
        uuid request_id FK
        text output
        datetime generated_at
    }
```

## AI Pipeline Diagram

```mermaid
flowchart LR
    Input[User Input / Dataset]
    Validate[Validation and Preprocessing]
    Retrieve[Knowledge Retrieval]
    Prompt[Prompt Builder]
    Model[LLM / ML Model]
    Guardrails[Validation and Safety Checks]
    Output[Structured Output]
    Feedback[User Feedback / Evaluation]

    Input --> Validate --> Retrieve --> Prompt --> Model --> Guardrails --> Output
    Output --> Feedback
    Feedback --> Prompt
```

For non-RAG systems, remove `Retrieve`. For supervised ML systems, replace `Prompt Builder` and `LLM / ML Model` with `Feature Extraction`, `Training`, and `Inference`.
