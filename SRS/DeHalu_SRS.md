# Software Requirements Specification

## DeHalu: Agentic Hallucination Detection and Mitigation for Local CodeLLMs

### 1. Project Overview

#### 1.1 Project Title

DeHalu: Agentic Hallucination Detection and Mitigation for Local CodeLLMs

#### 1.2 Problem Statement

Students and developers increasingly use local code-generating large language models because they are free, private, and available without subscription limits. However, local CodeLLMs may generate code that appears confident and syntactically plausible while containing hallucinated dependencies, fake APIs, invalid symbols, missing requirements, unsafe constructs, or logically incorrect behavior. When such code is accepted without verification, it can fail during integration, mislead the user, or introduce security and maintainability risks.

The problem is not only that generated code may contain ordinary programming errors. In hallucination cases, the model may invent facts about packages, APIs, language behavior, framework functions, or the user's intended requirements. These errors are difficult for users to detect because the response often includes fluent explanations and confident claims. Typical prompt-only solutions are insufficient because they depend on the same model's self-assessment, confidence scores alone do not prove correctness, and dynamic execution can be costly or unsafe for arbitrary generated code.

DeHalu addresses this problem by acting as a verification gateway between the user and a local CodeLLM. The system generates code, extracts checkable claims from the generated output, validates the claims using execution-free static analysis and tool-backed evidence, computes hallucination metrics, and either accepts, rejects, or repairs the output through a controlled mitigation loop.

#### 1.3 Objectives

- Detect code hallucinations before generated code is trusted by the user.
- Focus the committed verification scope on execution-free static analysis and tool-backed validation.
- Identify hallucination-related error types such as fake imports, invalid APIs, undefined symbols, requirement deviation, and unsafe structural patterns.
- Use a structured LLM-as-a-Judge pool and Chain-of-Verification checks as supporting verification signals, not as standalone proof.
- Provide transparent quantitative metrics and evidence for each accept, reject, or repair decision.
- Apply parameter-free mitigation through prompt structure, verification questions, and repair prompts instead of model fine-tuning.

#### 1.4 Scope

In scope:

- Natural-language prompt intake for code generation tasks.
- Automatic inference of target language, framework, runtime, and constraints when possible.
- Code generation using a local CodeLLM.
- Claim extraction from generated code and explanations.
- Execution-free syntax, AST, import, symbol, and package/API validation.
- Quantitative hallucination metrics including MiHN, MaHR, TR-S, entropy, and log-probability signals where available.
- LLM-as-a-Judge pool evaluation with strict rubrics for requirement alignment, functional logic, code quality, and safety.
- Chain-of-Verification based claim checking against static-analysis evidence.
- Policy-based accept, reject, warn, or repair decisions.
- Evidence reporting through backend records and a frontend monitoring interface.

Out of scope:

- Arbitrary dynamic execution of generated code as a required verification method.
- Training or fine-tuning a new CodeLLM.
- Full repository-level RAG or large external documentation retrieval as a required component.
- Complete vulnerability assessment equivalent to a dedicated security audit.
- Guaranteed proof of semantic correctness for every possible program.

#### 1.5 Deliverables

- A working web application that accepts natural-language programming prompts, generates code through a local CodeLLM, and returns verified, warned, rejected, or repaired code with evidence.
- A backend service exposing the prompt intake, code generation, claim extraction, static-analysis verification, metric calculation, judge evaluation, Chain-of-Verification, policy decision, and repair workflow APIs consumed by the frontend.
- An execution-free static verification pipeline that detects hallucination-raised errors such as fake imports, invalid APIs, undefined symbols, syntax or AST errors, unsupported assumptions, unsafe constructs, and requirement deviations.
- A live monitoring interface that visualizes each verification stage, including generated code, extracted claims, analyzer findings, hallucination metrics, judge and CoVe verdicts, policy decisions, and repair attempts.
- A persisted run-history and evidence store that supports later review by the student developer, supervisor, or evaluator.
- An academic SRS, design documentation, and evaluation report describing the system requirements, architecture, hallucination error taxonomy, static-analysis scope, and validation results.

### 2. Requirements Analysis

#### 2.1 Stakeholders

| Stakeholder | Role / Interest |
| --- | --- |
| Student Developer | Uses the system to generate safer code from local CodeLLMs. |
| System Maintainer | Maintains backend pipeline, model adapters, static analyzers, and frontend reporting. |
| Local CodeLLM Provider | Supplies generated code through a local inference runtime such as Ollama. |

#### 2.2 Hallucination Error Taxonomy

| Paper Category | Error Type | Primary Detection Responsibility |
| --- | --- | --- |
| Syntactic Hallucination | Syntax Violation | Tree-sitter or language-specific AST parser detects invalid syntax and malformed structures. |
| Syntactic Hallucination | Incomplete Code Generation | AST parsing and static heuristics detect incomplete blocks, missing definitions, and unfinished code. |
| Runtime Execution Hallucination | API Knowledge Conflict | Symbol indexer and package/API validation detect invented or incompatible APIs without executing code. |
| Runtime Execution Hallucination | Invalid Reference Errors | Symbol indexer and static reference analysis detect unresolved imports, undefined symbols, and invalid references. |
| Functional Correctness Hallucination | Incorrect Logical Flow | LLM-as-a-Judge pool evaluates semantic correctness using a strict functional logic rubric. |
| Functional Correctness Hallucination | Requirement Deviation | LLM-as-a-Judge pool compares prompt requirements, extracted behavioral claims, and generated code. |
| Code Quality Hallucination | Resource Mishandling | Semgrep/static rules detect known resource-misuse patterns; judge pool reviews broader semantic risks. |
| Code Quality Hallucination | Security Vulnerability | Semgrep/static rules detect known unsafe patterns; judge pool reviews remaining security concerns. |
| Code Quality Hallucination | Code Smell | Static rules and judge-pool review detect repeated, unclear, or low-quality generated structures. |

DeHalu addresses all four hallucination categories in the taxonomy. Its strongest deterministic coverage is for syntax, incomplete code, API conflicts, and invalid references. Functional correctness and broader code quality findings are handled as semantic evidence through the judge pool and policy layer rather than as absolute proof.

#### 2.3 Hallucination-Raised Error Mapping

| Hallucinated Claim or Behavior | Error Raised in Generated Code | Static Evidence Used by DeHalu | Policy Impact |
| --- | --- | --- | --- |
| Invented package or module exists | Missing dependency or unresolved import | Import resolver, package index lookup, AST import node | Repair or reject when the dependency is unsupported |
| Real package has an invented API | Invalid function, method, class, or parameter usage | Symbol table, framework metadata, API index evidence | Repair when a known replacement exists; otherwise warn or reject |
| Helper function or variable is assumed to exist | Undefined symbol or incomplete implementation | AST symbol collection and reference analysis | Repair or reject depending on severity |
| Generated code is structurally malformed | Syntax or parser error | Language parser error, malformed AST, incomplete block detection | Reject or repair before any user-facing acceptance |
| Code solves a different task than requested | Requirement deviation | Judge rubric, extracted behavioral claims, prompt-to-code checklist | Warn, repair, or reject based on missing requirement severity |
| Model repeats imports, blocks, or logic | Degenerated or repetitive output | TR-S score and repeated AST/text pattern detection | Warn or repair when repetition harms correctness |
| Risky operation is introduced without request | Unsafe construct generation | SAST rule, banned-call list, static sink/source pattern | Reject or repair because the risk is not user-authorized |
| Model assumes a version, framework, or input property | Unsupported environment assumption | Inference uncertainty flag, dependency metadata, requirement comparison | Warn or repair by removing the assumption |

#### 2.4 Why Typical Solutions Are Insufficient

| Typical Solution | Limitation for Hallucination Errors |
| --- | --- |
| Asking the same model to self-check | The model may repeat the same invented fact with confidence and fail to challenge its own assumptions. |
| Relying on natural-language confidence | Confident wording does not correlate reliably with real API existence, requirement satisfaction, or code validity. |
| Simple linting only | Linters can detect some syntax and style issues but may miss fake package claims, invalid API semantics, and requirement deviations. |
| Dynamic execution as the main method | Executing arbitrary generated code introduces safety risk, environment overhead, and incomplete coverage for code paths not exercised. |
| Fine-tuning a larger model | Fine-tuning requires compute, data, and maintenance effort that are not practical for the project's student-budget local-LLM target. |
| RAG-only validation | Retrieval helps when documentation is available, but it does not by itself enforce deterministic claim extraction, policy decisions, or repair verification. |

The proposed system therefore treats static analysis and tool-backed claim validation as the primary evidence layer. LLM-based judging and Chain-of-Verification are used to organize and interpret evidence, but they shall not replace deterministic static findings.

#### 2.5 Functional Requirements

##### Prompt Intake and Inference

- FR-1.1: Users shall submit a natural-language programming prompt.
- FR-1.2: The system shall infer the likely target language from the prompt when the user does not state it.
- FR-1.3: The system shall infer framework, runtime, and constraint assumptions when they are clearly implied.
- FR-1.4: The system shall mark uncertain inferred assumptions as evidence rather than treating them as confirmed facts.
- FR-1.5: The system shall reject or request clarification for prompts that are too ambiguous for meaningful verification.

##### Code Generation

- FR-2.1: The system shall send the normalized prompt to a local CodeLLM.
- FR-2.2: The system shall store the generated code, model identifier, prompt metadata, and generation timestamp for each run.
- FR-2.3: The system shall capture token log-probability and predictive entropy signals when the selected model provider exposes them.
- FR-2.4: The system shall separate generated code from explanatory text when possible.

##### Claim Extraction

- FR-3.1: The system shall extract imports, packages, APIs, symbols, functions, classes, and runtime assumptions from generated code.
- FR-3.2: The system shall extract behavioral claims from generated explanations when they are present.
- FR-3.3: The system shall assign each claim a stable claim identifier.
- FR-3.4: The system shall classify each claim by type, including dependency, API, symbol, behavior, safety, or assumption.

##### Execution-Free Static Analysis

- FR-4.1: The system shall parse generated code without executing it.
- FR-4.2: The system shall detect syntax and AST structure errors.
- FR-4.3: The system shall detect undefined symbols where language adapters support symbol analysis.
- FR-4.4: The system shall detect unsupported imports and suspicious dependency references.
- FR-4.5: The system shall apply static security and quality rules to identify unsafe generated constructs.
- FR-4.6: The system shall report static-analysis findings with severity, location, rule identifier, and explanation where available.

##### Tool-Backed Package and API Validation

- FR-5.1: The system shall validate referenced packages against configured package or symbol indexes when available.
- FR-5.2: The system shall validate referenced APIs against language or framework metadata when available.
- FR-5.3: The system shall mark unverifiable package or API claims as uncertain instead of silently accepting them.
- FR-5.4: The system shall use tool-backed evidence as a primary signal for dependency and API hallucination decisions.

##### Quantitative Metric Engine

- FR-6.1: The system shall compute Micro Hallucination Number for invalid or unsupported micro-level code claims.
- FR-6.2: The system shall compute Macro Hallucination Rate for the proportion of hallucinated claims in an output.
- FR-6.3: The system shall compute TR-S or an equivalent structural repetition score for repeated generated structures.
- FR-6.4: The system shall correlate static invalid-reference evidence with entropy or log-probability spikes when available.
- FR-6.5: The system shall use metrics as evidence signals for severity ranking, policy decisions, and before/after repair comparison.
- FR-6.6: The system shall expose metrics as part of the final verification report.

##### LLM-as-a-Judge Pool Verification

- FR-7.1: The system shall evaluate generated code using a pool of structured LLM-as-a-Judge evaluators.
- FR-7.2: The judge pool shall include rubric coverage for requirement alignment, functional logic, code quality, safety, unsupported assumptions, dependency plausibility, and API validity.
- FR-7.3: Each judge shall produce structured scores and findings instead of only free-form text.
- FR-7.4: The system shall aggregate judge outputs into a consensus verdict with average score and agreement level.
- FR-7.5: Judge findings shall not override deterministic static-analysis failures.

##### Chain-of-Verification

- FR-8.1: The system shall convert extracted claims into targeted verification questions.
- FR-8.2: The system shall answer verification questions using static-analysis findings and tool-backed evidence.
- FR-8.3: The system shall classify each checked claim as supported, unsupported, or uncertain.
- FR-8.4: The system shall include unsupported and uncertain claims in the policy decision.

##### Policy Decision and Mitigation

- FR-9.1: The system shall combine static findings, metric scores, judge consensus, and CoVe results into a deterministic policy decision.
- FR-9.2: The system shall support at least four policy outcomes: accept, warn, repair, and reject.
- FR-9.3: The system shall trigger repair when blocking hallucination evidence is detected and repair is allowed.
- FR-9.4: The repair agent shall receive the failed code and evidence-backed failure context.
- FR-9.5: The repaired code shall pass through the verification pipeline again before being returned.
- FR-9.6: The system shall limit repair attempts to prevent unbounded loops.

##### Evidence Reporting and Monitoring

- FR-10.1: The system shall show the final generated or repaired code to the user.
- FR-10.2: The system shall show the policy decision and hallucination risk evidence.
- FR-10.3: The system shall display stage-level results for generation, claim extraction, static analysis, metrics, judge verification, CoVe, policy, and repair.
- FR-10.4: The system shall persist run history and evidence for later review.
- FR-10.5: The frontend shall provide a live or near-real-time view of the verification workflow when backend events are available.

#### 2.6 Non-Functional Requirements

| ID | Category | Requirement |
| --- | --- | --- |
| NFR-1 | Security | The system shall not execute arbitrary generated code as part of the committed verification scope. |
| NFR-2 | Privacy | The system shall support local CodeLLM generation so user prompts and code can remain on the user's machine when configured locally. |
| NFR-3 | Reliability | The system shall fail closed by warning or rejecting output when blocking verification stages fail or evidence is insufficient. |
| NFR-4 | Explainability | The system shall provide evidence for each accept, warn, repair, or reject decision. |
| NFR-5 | Maintainability | Language-specific parsing and validation logic shall be isolated behind language adapters. |
| NFR-6 | Extensibility | The system shall allow additional analyzers, package registries, model providers, and judge rubrics to be added without rewriting the whole pipeline. |
| NFR-7 | Performance | The system shall complete static verification for typical single-file generated code within an interactive response window suitable for student use. |
| NFR-8 | Compatibility | The frontend shall support modern desktop browsers and responsive layouts for common laptop screen sizes. |
| NFR-9 | Auditability | The system shall persist prompt, model, generated output, extracted claims, findings, metrics, and policy decisions for each run. |
| NFR-10 | Usability | The system shall present verification results in a form understandable to users who may not know the internal analyzer tools. |

### 3. System Modeling

#### 3.1 System-Level Use Case Diagram

```mermaid
flowchart LR
    User((User))
    LocalModel[Local CodeLLM Provider]
    StaticAnalyzers[Static Analyzers]

    subgraph DeHalu[DeHalu System]
        UC1[Submit Prompt]
        UC2[Generate Code]
        UC3[Extract Claims]
        UC4[Run Static Verification]
        UC5[Review Evidence]
        UC6[Repair Hallucinated Code]
    end

    User --> UC1
    UC1 --> UC2
    UC2 --> LocalModel
    UC2 --> UC3
    UC3 --> UC4
    UC4 --> StaticAnalyzers
    UC4 --> UC5
    UC5 --> UC6
    User --> UC5
```

#### 3.2 Use Case Descriptions

| Use Case ID | Use Case | Primary Actor | Preconditions | Main Flow | Outcome |
| --- | --- | --- | --- | --- | --- |
| UC-1 | Submit Prompt | Student Developer | User has access to the application | User enters a programming request; system normalizes and infers missing constraints | A normalized generation request is created |
| UC-2 | Generate Code | Student Developer | A normalized prompt exists | System sends prompt to local CodeLLM; model returns code and metadata | Initial code draft is available |
| UC-3 | Extract Claims | System | Generated code is available | System extracts imports, APIs, symbols, assumptions, and behavior claims | Structured claim list is produced |
| UC-4 | Run Static Verification | System | Claims and code are available | System parses code and validates claims using static analyzers and tool evidence | Static findings and validation results are produced |
| UC-5 | Review Evidence | Student Developer | Verification is complete | System shows metrics, findings, policy decision, and evidence | User understands why output was accepted, warned, repaired, or rejected |
| UC-6 | Repair Hallucinated Code | System | Policy decision allows repair | Repair agent receives failed code and evidence; repaired code is reverified | Repaired code is accepted, warned, or rejected |

#### 3.3 System-Level Activity Diagram

```mermaid
flowchart TD
    Start([Start])
    Prompt[User submits prompt]
    Normalize[Infer language, framework, runtime, and constraints]
    Ambiguous{Prompt verifiable?}
    Clarify[Request clarification or mark uncertain assumptions]
    Generate[Generate code with local CodeLLM]
    Claims[Extract checkable claims]
    Static[Run execution-free static analysis]
    Validate[Validate packages, APIs, and symbols]
    Metrics[Compute MiHN, MaHR, TR-S, entropy/log-prob signals]
    JudgePool[Run LLM-as-a-Judge pool]
    Consensus[Aggregate judge consensus]
    CoVe[Run Chain-of-Verification checks]
    Policy{Policy decision}
    Accept[Return verified code and evidence]
    Warn[Return code with warning and evidence]
    Repair[Repair using failure context]
    Reject[Reject output with explanation]
    Reverify[Re-run verification on repaired code]
    End([End])

    Start --> Prompt --> Normalize --> Ambiguous
    Ambiguous -- No --> Clarify --> Normalize
    Ambiguous -- Yes --> Generate --> Claims --> Static --> Validate --> Metrics --> JudgePool --> Consensus --> CoVe --> Policy
    Policy -- Accept --> Accept --> End
    Policy -- Warn --> Warn --> End
    Policy -- Repair --> Repair --> Reverify --> Policy
    Policy -- Reject --> Reject --> End
```

#### 3.4 Detection Use Case Diagram

The detection use case diagram focuses on the execution-free hallucination detection workflow before any repair action is triggered.

```mermaid
flowchart LR
    User((User))
    LocalModel[Local CodeLLM Provider]
    StaticAnalyzers[Static Analyzers]
    SymbolIndex[Package / Symbol Index]
    JudgePool[Judge Pool]

    subgraph Detection[DeHalu Detection Module]
        DUC1[Submit Programming Prompt]
        DUC2[Generate Initial Code]
        DUC3[Log Generation Metrics]
        DUC4[Extract Checkable Claims]
        DUC5[Parse Syntax and AST]
        DUC6[Run Static Rules]
        DUC7[Validate Packages and APIs]
        DUC8[Calculate Hallucination Metrics]
        DUC9[Evaluate Semantic Correctness]
        DUC10[Aggregate Judge Consensus]
        DUC11[Make Detection Verdict]
    end

    User --> DUC1
    DUC1 --> DUC2
    DUC2 --> LocalModel
    DUC2 --> DUC3
    DUC2 --> DUC4
    DUC4 --> DUC5
    DUC4 --> DUC6
    DUC4 --> DUC7
    DUC5 --> StaticAnalyzers
    DUC6 --> StaticAnalyzers
    DUC7 --> SymbolIndex
    DUC5 --> DUC8
    DUC6 --> DUC8
    DUC7 --> DUC8
    DUC8 --> DUC9
    DUC9 --> JudgePool
    JudgePool --> DUC10
    DUC10 --> DUC11
    DUC11 --> User
```

#### 3.5 Detection Activity Diagram

This activity diagram expands the static detection path into parser, SAST, symbol-validation, metric, judge, and policy-verdict stages.

```mermaid
flowchart TD
    Start([Start Detection])
    Prompt[Receive normalized user prompt]
    Generate[Generate initial code with local CodeLLM]
    LogMetrics[Capture entropy and log-probability signals when available]
    Extract[Extract imports, APIs, symbols, assumptions, and behavioral claims]
    Parse[Parse code using syntax and AST parser]
    ParseOK{Syntax and structure valid?}
    SyntaxFinding[Record syntax, AST, or incomplete-code finding]
    StaticRules[Run static rules for unsafe constructs and quality patterns]
    SymbolCheck[Validate imports, packages, APIs, and symbols]
    Evidence[Normalize all static findings and claim evidence]
    Metrics[Compute MiHN, MaHR, TR-S, and uncertainty correlation]
    JudgePool[Run judge pool for requirement alignment, functional logic, quality, and safety]
    Consensus[Aggregate final judge verdict, average score, and agreement level]
    CoVe[Run Chain-of-Verification over extracted claims]
    Decision{Blocking hallucination evidence?}
    Verified[Mark output as verified or low risk]
    Warn[Mark output as uncertain or warning]
    RepairNeeded[Send failure context to mitigation module]
    End([End Detection])

    Start --> Prompt --> Generate --> LogMetrics --> Extract --> Parse --> ParseOK
    ParseOK -- No --> SyntaxFinding --> Evidence
    ParseOK -- Yes --> StaticRules --> SymbolCheck --> Evidence
    Evidence --> Metrics --> JudgePool --> Consensus --> CoVe --> Decision
    Decision -- No --> Verified --> End
    Decision -- Uncertain --> Warn --> End
    Decision -- Yes --> RepairNeeded --> End
```

#### 3.6 Mitigation Use Case Diagram

The mitigation use case diagram focuses on what happens after the detection module finds unsupported, unsafe, or uncertain claims that require repair.

```mermaid
flowchart LR
    User((User))
    DetectionModule[Detection Module]
    LocalModel[Local CodeLLM Provider]
    StaticAnalyzers[Static Analyzers]

    subgraph Mitigation[DeHalu Mitigation Module]
        MUC1[Receive Detection Findings]
        MUC2[Build Failure Context]
        MUC3[Generate Verification Questions]
        MUC4[Convert Findings into CoVe Facts]
        MUC5[Repair Hallucinated Code]
        MUC6[Re-run Static Verification]
        MUC7[Recalculate Metrics]
        MUC8[Apply Repair Policy]
        MUC9[Return Repaired or Rejected Result]
    end

    DetectionModule --> MUC1
    MUC1 --> MUC2
    MUC2 --> MUC3
    MUC3 --> MUC4
    MUC4 --> MUC5
    MUC5 --> LocalModel
    MUC5 --> MUC6
    MUC6 --> StaticAnalyzers
    MUC6 --> MUC7
    MUC7 --> MUC8
    MUC8 --> MUC9
    MUC9 --> User
```

#### 3.7 Mitigation Activity Diagram

This activity diagram expands the repair loop. Repaired code is not returned directly; it must pass through static verification again before acceptance.

```mermaid
flowchart TD
    Start([Start Mitigation])
    Findings[Receive unsupported claims, static findings, metrics, and judge/CoVe verdicts]
    Classify[Classify failures by dependency, API, symbol, syntax, safety, repetition, or requirement deviation]
    Repairable{Repair allowed and attempt limit not reached?}
    Reject[Reject output with evidence]
    BuildContext[Build evidence-backed failure context]
    Questions[Generate targeted verification questions]
    Facts[Convert verified answers into repair facts]
    RepairPrompt[Create constrained repair prompt]
    RepairAgent[Generate repaired code with local CodeLLM]
    ExtractAgain[Extract claims from repaired code]
    StaticAgain[Run execution-free static verification again]
    MetricsAgain[Recalculate hallucination metrics]
    Compare[Compare initial and repaired hallucination risk]
    Policy{Repair passed policy?}
    ReturnRepair[Return repaired code with evidence]
    Retry{Another repair attempt allowed?}
    Loop[Send new findings back to failure context]
    End([End Mitigation])

    Start --> Findings --> Classify --> Repairable
    Repairable -- No --> Reject --> End
    Repairable -- Yes --> BuildContext --> Questions --> Facts --> RepairPrompt --> RepairAgent
    RepairAgent --> ExtractAgain --> StaticAgain --> MetricsAgain --> Compare --> Policy
    Policy -- Yes --> ReturnRepair --> End
    Policy -- No --> Retry
    Retry -- Yes --> Loop --> BuildContext
    Retry -- No --> Reject --> End
```

### 4. Data and Information Modeling

#### 4.1 Database Schema

| Table | Key Fields |
| --- | --- |
| sessions | id (PK), created_at, last_active |
| runs | id (PK), session_id (FK, nullable), prompt, inferred_language, model_name, status, max_retry, created_at, completed_at |
| generated_outputs | id (PK), run_id (FK), attempt_no, code, explanation, provider, entropy_summary, logprob_summary |
| claims | id (PK), output_id (FK), claim_type, claim_text, location, status |
| static_findings | id (PK), output_id (FK), rule_id, severity, message, location, evidence_source |
| metric_results | id (PK), output_id (FK), mihn, mahr, tr_s, entropy_score, overall_score |
| judge_results | id (PK), output_id (FK), judge_name, judge_model, verdict, score, rubric_json, explanation, created_at |
| judge_consensus | id (PK), output_id (FK), final_verdict, average_score, agreement_level, summary |
| cove_results | id (PK), output_id (FK), claim_id (FK), verdict, evidence, confidence |
| policy_decisions | id (PK), run_id (FK), output_id (FK), decision, reason, created_at |

Note: Field names are proposed for SRS modeling. The implementation may use equivalent names while preserving the same information responsibilities.

#### 4.2 ER Diagram

The ER diagram models the main persistence entities for prompt submissions, generated outputs, extracted claims, static-analysis evidence, hallucination metrics, judge and CoVe results, and final policy decisions.

```mermaid
erDiagram
    SESSIONS ||--o{ RUNS : groups
    RUNS ||--o{ GENERATED_OUTPUTS : produces
    RUNS ||--o{ POLICY_DECISIONS : receives
    GENERATED_OUTPUTS ||--o{ CLAIMS : contains
    GENERATED_OUTPUTS ||--o{ STATIC_FINDINGS : has
    GENERATED_OUTPUTS ||--o| METRIC_RESULTS : summarizes
    GENERATED_OUTPUTS ||--o{ JUDGE_RESULTS : evaluated_by
    GENERATED_OUTPUTS ||--o| JUDGE_CONSENSUS : aggregates
    GENERATED_OUTPUTS ||--o{ COVE_RESULTS : verified_by
    GENERATED_OUTPUTS ||--o{ POLICY_DECISIONS : informs
    CLAIMS ||--o{ COVE_RESULTS : checked_by

    SESSIONS {
        string id PK
        datetime created_at
        datetime last_active
    }

    RUNS {
        string id PK
        string session_id FK
        text prompt
        string inferred_language
        string model_name
        string status
        int max_retry
        datetime created_at
        datetime completed_at
    }

    GENERATED_OUTPUTS {
        string id PK
        string run_id FK
        int attempt_no
        text code
        text explanation
        string provider
        json entropy_summary
        json logprob_summary
    }

    CLAIMS {
        string id PK
        string output_id FK
        string claim_type
        text claim_text
        string location
        string status
    }

    STATIC_FINDINGS {
        string id PK
        string output_id FK
        string rule_id
        string severity
        text message
        string location
        string evidence_source
    }

    METRIC_RESULTS {
        string id PK
        string output_id FK
        float mihn
        float mahr
        float tr_s
        float entropy_score
        float overall_score
    }

    JUDGE_RESULTS {
        string id PK
        string output_id FK
        string judge_name
        string judge_model
        string verdict
        float score
        json rubric_json
        text explanation
        datetime created_at
    }

    JUDGE_CONSENSUS {
        string id PK
        string output_id FK
        string final_verdict
        float average_score
        string agreement_level
        text summary
    }

    COVE_RESULTS {
        string id PK
        string output_id FK
        string claim_id FK
        string verdict
        text evidence
        float confidence
    }

    POLICY_DECISIONS {
        string id PK
        string run_id FK
        string output_id FK
        string decision
        text reason
        datetime created_at
    }
```

#### 4.3 Dataset and Evidence Sources

| Dataset / Source | Data Type | Purpose | Preprocessing | Privacy / Risk |
| --- | --- | --- | --- | --- |
| User prompts | Natural language text | Define programming task and constraints | Normalize language, framework, runtime, and ambiguity | May contain private code or requirements; store minimally |
| Generated code | Source code text | Subject of hallucination detection | Split code from explanation; parse by language | May contain sensitive logic if user provided context |
| Static analyzer output | Structured findings | Detect syntax, symbol, dependency, and safety issues | Normalize severity, rule ID, message, and location | Low privacy risk but linked to code |
| Package/API index evidence | Structured lookup results | Validate whether packages and APIs exist | Normalize package, symbol, version, and status | External lookup may reveal dependency names if online lookup is used |
| Judge and CoVe outputs | Structured JSON verdicts | Evaluate requirement alignment and claim support | Validate schema and normalize scores | May repeat code or prompt content; store with access control |

### 5. AI Engineering Design

#### 5.1 AI Pipeline

```mermaid
flowchart LR
    Prompt[User Prompt]
    Normalize[Prompt Normalization]
    Generate[Local CodeLLM Generation]
    Claims[Claim Extraction]
    Static[Static Analysis]
    Tools[Package and API Validation]
    Metrics[Metric Engine]
    JudgePool[LLM-as-a-Judge Pool]
    Consensus[Judge Consensus]
    CoVe[Chain-of-Verification]
    Policy[Policy Decision]
    Repair[Repair Agent]
    Output[Final Code and Evidence]

    Prompt --> Normalize --> Generate --> Claims
    Claims --> Static
    Claims --> Tools
    Static --> Metrics
    Tools --> Metrics
    Metrics --> JudgePool --> Consensus --> CoVe --> Policy
    Policy -->|accept / warn / reject| Output
    Policy -->|repair| Repair --> Claims
```

The metric engine does not act as the only decision maker. It quantifies hallucination evidence, ranks severity, correlates static failures with generation uncertainty where available, supports the policy gateway, and measures whether repair reduces risk across repeated attempts.

#### 5.2 Model Selection

| Component | Candidate / Choice | Reason |
| --- | --- | --- |
| Code Generator | Local 3B-7B parameter CodeLLM through Ollama or equivalent local runtime | Fits student-budget hardware and supports privacy-preserving local generation. |
| Judge Pool | At least three structured judges using strong local or optional external models during evaluation | Separate judge roles can assess requirement alignment, functional logic, and code quality or safety while deterministic evidence remains primary. |
| Judge Consensus | Aggregation policy over individual judge results | Produces final semantic verdict, average score, and agreement level for the policy gateway. |
| Repair Agent | Same local CodeLLM with strict repair prompt | Keeps mitigation parameter-free and avoids separate model training. |
| Static Parser | Tree-sitter or language-specific AST parser | Enables execution-free syntax and structure analysis across languages. |
| SAST Rules | Semgrep or equivalent static rule engine | Detects structural, security, and unsafe-code patterns without executing code. |
| Symbol Indexer | Language-specific symbol indexer with generic fallback | Supports static detection of API knowledge conflicts and invalid reference errors in a language-agnostic architecture. |

#### 5.3 Prompt Design

| Prompt / Agent | Inputs | Expected Output | Constraints |
| --- | --- | --- | --- |
| Normalization Prompt | User prompt | Inferred language, framework, runtime, constraints, uncertainty flags | Must not invent unstated requirements as facts. |
| Code Generation Prompt | Normalized task | Code, assumptions, dependencies, brief explanation | Must separate code from assumptions and avoid unsupported package claims. |
| Requirement Judge Prompt | Prompt, generated code, claims, static findings, metrics | Requirement-alignment score and deviation findings | Must compare implementation behavior against the original user request. |
| Functional Logic Judge Prompt | Prompt, generated code, claims, static findings, metrics | Functional correctness score and logical-flow findings | Must identify likely incorrect logic without executing generated code. |
| Quality and Safety Judge Prompt | Prompt, generated code, claims, static findings, metrics | Code quality, resource-use, and safety findings | Must use static evidence where available and mark uncertain findings clearly. |
| Judge Consensus Prompt | Individual judge outputs | Final semantic verdict, average score, agreement level, and summary | Must aggregate judge results without overriding deterministic static failures. |
| CoVe Prompt | Extracted claims and evidence | Claim-level supported, unsupported, or uncertain verdicts | Must verify claims against evidence rather than model confidence alone. |
| Repair Prompt | Failed code and evidence-backed failure context | Repaired code and repair explanation | Must only fix evidence-supported issues and avoid adding new unsupported dependencies. |

#### 5.4 Evaluation and Validation Method

The system shall be evaluated using prompt cases that intentionally trigger common hallucination errors:

- Fake library or package names.
- Real libraries with invalid APIs.
- Undefined symbols or missing helper functions.
- Syntax errors and incomplete code blocks.
- Requirement deviation where the output solves a different task.
- Repetitive or degenerated code structures.
- Unsafe operations not required by the prompt.

Evaluation shall compare initial generated outputs against verified or repaired outputs using static findings, claim-level verdicts, metric changes, judge consensus, and final policy decisions. Metric changes shall be used to show whether repair reduced hallucination evidence, such as lower MiHN, MaHR, TR-S, or uncertainty-linked static failure scores.

#### 5.5 Safety and Privacy Controls

- The committed verification flow shall not execute arbitrary generated code.
- External package or API lookups shall be configurable so the system can run in local-only mode.
- Stored prompts, generated code, and verification evidence shall be treated as sensitive project data.
- The system shall expose uncertainty when evidence is incomplete instead of presenting unverifiable output as fully verified.

### 6. Completeness Check

This SRS is based on the revised DeHalu proposal and the stated proposal feedback. It intentionally prioritizes an execution-free, static-analysis-centered verification scope. Existing repository files that mention sandbox execution should be treated as older or broader implementation notes unless the project scope is later changed. Database fields and tool choices are proposed at the SRS level and may be mapped to equivalent implementation names.
