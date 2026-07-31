# Project Proposal Form

**Institute of Information Technology (IIT)**  
**University of Dhaka**

**Student's Name:** [Your Name]  
**Student's Roll:** [Your Roll]  
**Phone:** [Your Phone Number]

# DeHalu: Agentic Hallucination Detection and Mitigation for Code Generation LLMs

## Motivation

Local Large Language Models are increasingly used to generate software code, but their outputs are not always reliable. CodeLLMs can produce several forms of code hallucination, including syntactic hallucinations such as syntax violations and incomplete code, runtime execution hallucinations such as API knowledge conflicts and invalid references, functional correctness hallucinations such as incorrect logical flow and requirement deviation, and code quality hallucinations such as resource mishandling, security vulnerabilities, and code smells.

These issues are especially risky because generated code can look fluent, confident, and structurally plausible even when it is incorrect, impossible to execute, or inconsistent with the user's intent. Without a verification layer, users may accept code that does not compile, imports fake dependencies, misuses APIs, fails under transformed inputs, or silently violates requirements. This motivates the need for an agentic detection and mitigation pipeline that verifies generated code before it is trusted or reused.

## Project Description

DeHalu is an agentic verification gateway for CodeLLMs, focused on detecting and mitigating hallucinations in generated code before the output is trusted by the user. The target generator is a local Ollama-hosted CodeLLM. After code generation, DeHalu passes the output through a structured verification pipeline consisting of prompt clarification, Chain-of-Thought-style structured reasoning, claim extraction, static analysis, sandbox execution, tool-backed package/API validation, LLM-as-a-Judge verification, Chain-of-Verification, panel consensus, policy decision, and repair-based mitigation. Instead of returning raw model output directly, DeHalu provides a verified, rejected, or repaired result with evidence explaining what was checked and why the final decision was made.

The project aims to make code generation safer, more transparent, and more trustworthy by showing the full orchestration flow from prompt intake to final result.

## Problem Statement & Objectives

CodeLLMs often hallucinate libraries, APIs, package names, functions, runtime behavior, and implementation details. Existing code-generation interfaces usually show the final code without a detailed verification trail. As a result, users may trust generated code that does not compile, imports fake dependencies, uses invalid symbols, or claims unrealistic performance.

The main objective of DeHalu is to build a practical hallucination detection and mitigation system for CodeLLM outputs. The system will not rely only on model confidence. Instead, it will combine deterministic checks, execution-based verification, tool-backed dependency validation, and multiple verifier agents before deciding whether to accept, reject, or repair generated code.

Specific objectives:

- Accept a simple user prompt and infer language, framework, runtime, and constraints when possible.
- Generate code using a CodeLLM while recording provider, model, assumptions, dependencies, and execution notes.
- Extract verifiable claims from the generated code, including imports, APIs, symbols, and behavioral promises.
- Detect hallucinations using static analysis, sandbox execution, tool-based package/API validation, LLM judges, and Chain-of-Verification.
- Use Chain-of-Thought-style structured reasoning to improve task decomposition, verification planning, and repair prompts while validating final decisions through external evidence.
- Apply metamorphic relation checks for selected functional correctness cases where exact oracle outputs are difficult to define.
- Fuse evidence into interpretable hallucination metrics such as dependency plausibility, API validity, execution validity, and unsupported assumptions.
- Trigger mitigation or repair when deterministic or semantic verification fails.
- Present the full CrewAI orchestration flow through a live frontend so users can understand which agent, model, or tool performed each step.

The committed detection scope primarily covers syntactic hallucinations, runtime execution hallucinations, API/dependency hallucinations, invalid reference errors, and selected functional correctness issues such as requirement deviation. Code quality hallucinations such as resource mishandling, security vulnerabilities, and code smells are treated as limited-scope checks or future extensions, because full security auditing and maintainability analysis would require dedicated tools and evaluation benchmarks.

## Proposed Solution

- **Prompt Intake and Clarification:** The user provides only a natural-language prompt. The system clarifies or infers language, framework, runtime, and constraints without requiring the user to configure technical options manually.

- **Chain-of-Thought-Style Structured Reasoning:** The tool uses structured reasoning prompts to decompose the task, plan verification steps, and guide repair. Raw reasoning traces are not treated as proof of correctness; they are validated through static analysis, sandbox execution, tool-backed checks, LLM-as-a-Judge verification, and Chain-of-Verification.

- **Code Generation:** A local Ollama-hosted CodeLLM generates the initial implementation. The architecture remains provider-agnostic so that cloud models can be used during development or comparison, but the intended evaluation focus is hallucination detection and mitigation for local CodeLLMs.

- **Claim Extraction:** The generated output is decomposed into checkable claims such as imported packages, referenced APIs, declared symbols, runtime assumptions, and claimed behavior.

- **Static Analysis:** The code is inspected without execution to identify syntax errors, unsupported imports, dangerous calls, undefined symbols, and structural issues.

- **Sandbox Execution:** The code is compiled or executed in a controlled environment to detect runtime errors, import failures, timeout risks, and unsafe behavior.

- **Metamorphic Relation Checks:** For selected functional correctness cases, the system can generate requirement-preserving input transformations and verify whether the generated code maintains expected behavioral relations. This helps detect incorrect logical flow and requirement deviation when exact expected outputs are not available for every test case.

- **Tool-Backed Validation:** Package and API validation tools check whether referenced libraries, imports, and symbols are real. This supports detection of API knowledge conflicts and invalid reference errors. The system may use package registries such as PyPI where allowed, but repository-level RAG is not part of the committed mitigation scope.

- **LLM-as-a-Judge Verification:** Independent verifier models evaluate whether the generated code satisfies the prompt, whether its assumptions are valid, and whether the evidence suggests hallucination.

- **Chain-of-Verification (CoVe):** The system converts generated claims into targeted verification questions and checks them individually, reducing the chance that a fluent but incorrect answer is accepted.

- **Panel Consensus and Metric Fusion:** Multiple verification signals are combined into fused metrics, including requirement alignment, dependency plausibility, API symbol validity, execution validity, unsupported assumptions, and overall hallucination risk.

- **Policy Decision:** A deterministic policy layer decides whether to accept, reject, request clarification, or repair the output. Deterministic failures such as syntax errors, sandbox failures, and unsupported dependencies can trigger mitigation.

- **Mitigation and Repair:** The project focuses on parameter-free mitigation methods: prompt enhancement, Chain-of-Thought-style structured reasoning, Chain-of-Verification, multi-agent verification, and post-generation repair. If repair is possible, a repair agent receives the failed code and verification evidence, fixes the issues, and sends the repaired code back through the verification pipeline.

- **Policy and Thresholding:** DeHalu does not rely on a single fixed hallucination threshold such as 40% or 50%. Instead, mitigation is triggered by a strict policy engine using deterministic failures and verifier verdicts. Syntax errors, sandbox failures, unsupported imports, judge failures, CoVe failures, and high-risk warnings can trigger repair. Hallucination scores are still recorded and displayed as evidence, but the mitigation decision is primarily rule- and verdict-driven.

- **Live Orchestration Frontend:** A Next.js frontend visualizes the full pipeline as a live execution graph, showing each agent, model, tool, status, duration, evidence, policy decision, and final result.

## Key Technologies & Tools

**Languages:** Python, TypeScript  
**Backend Framework:** FastAPI  
**Frontend Framework:** Next.js, React  
**Agent Orchestration:** CrewAI  
**Code Generator:** Local Ollama-hosted CodeLLM  
**Optional/Experimental Providers:** Gemini, Groq, Mistral, Cerebras  
**Verification Techniques:** Static analysis, sandbox execution, metamorphic relation checks, tool-backed API/package validation, LLM-as-a-Judge, Chain-of-Verification, panel consensus, metric fusion  
**Mitigation Strategy:** Parameter-free mitigation using prompt enhancement, CoT-style structured reasoning, CoVe, multi-agent verification, and post-generation repair  
**Tool Validation:** Package registry lookup, API/symbol validation, PyPI lookup, MCP-ready tool gateway  
**Database & Persistence:** SQLAlchemy, SQLite for development, PostgreSQL-ready architecture, Alembic migrations  
**Frontend UI:** shadcn/ui, Tailwind CSS, React Flow, Framer Motion, Zustand, TanStack Query  
**Testing:** Pytest, Vitest, Cypress  
**Version Control:** Git, GitHub

## Timeline

| Phase | Duration | Activities | Expected Output |
| --- | --- | --- | --- |
| Phase 1: Research and Requirement Analysis | Week 1-2 | Study code hallucination types, verification methods, CoVe, judge-based evaluation, and execution-based detection | Requirement specification and literature summary |
| Phase 2: Backend Core Pipeline | Week 3-5 | Build prompt normalization, CodeLLM generation, claim extraction, static analysis, sandbox execution, and evidence persistence | Working backend verification pipeline |
| Phase 3: Agentic Orchestration | Week 6-7 | Integrate CrewAI agents for clarification, generation, verification, policy, and repair | Agent-based hallucination detection workflow |
| Phase 4: Mitigation and Tool Support | Week 8-9 | Add parameter-free mitigation using prompt enhancement, CoVe, metamorphic relation checks for selected functional cases, repair loop, package/API validation, tool gateway, and strict policy decisions | Hallucination mitigation with evidence-backed repair |
| Phase 5: Frontend MVP | Week 10-11 | Build prompt workspace, live orchestration graph, stage inspector, metrics panel, evidence timeline, and final code view | Interactive frontend for end-to-end runs |
| Phase 6: Testing and Evaluation | Week 12-13 | Test with valid prompts, fake APIs, non-existent libraries, syntax errors, unsafe code, and ambiguous prompts | Test report and evaluation results |
| Phase 7: Documentation and Finalization | Week 14 | Prepare final report, user guide, architecture documentation, and presentation materials | Final project submission package |

## Expected Outcome

The final system will provide an end-to-end demonstration of hallucination-aware code generation. Users will submit a programming prompt, receive generated or repaired code, and see a transparent evidence trail showing how the system detected or mitigated hallucinations. The project will demonstrate that hallucinations from local CodeLLMs can be detected and mitigated through parameter-free methods that combine deterministic verification, runtime checks, metamorphic relation checks for selected functional behaviors, tool-backed validation, multi-agent reasoning, Chain-of-Verification, and policy-controlled repair.

## Future Work

Future extensions may include repository-level RAG, API documentation retrieval, security vulnerability scanning, resource-misuse detection, code smell analysis, broader automated test generation, expanded metamorphic relation libraries, and benchmark-based threshold calibration. These are not part of the committed proposal scope but are compatible with the system architecture.

## References

[1] "CodeHalu: Investigating Code Hallucinations in LLMs via Execution-based Verification," arXiv:2405.00253.

[2] "Hallucination by Code Generation LLMs: Taxonomy, Benchmarks, Mitigation," arXiv:2504.20799.

[3] "An Empirical Analysis of Static Analysis Methods for Detection and Mitigation of Code Library Hallucinations," arXiv:2604.07755.

[4] "Chain-of-Verification Reduces Hallucination in Large Language Models," arXiv:2309.11495.

[5] "Chain-of-Thought Prompting Elicits Reasoning in Large Language Models," arXiv:2201.11903.

[6] "Chain-of-Thought Prompting Obscures Hallucination," arXiv:2506.17088.

[7] "ClarifyGPT: A Framework for Enhancing LLM-Based Code Generation through Requirements Clarification."

[8] "Systematic Literature Review of Code Hallucinations," arXiv:2511.00776.

## Supervisor Information

**Supervisor's Name:** [Supervisor's Name]  
**Signature of the Supervisor:**  
**Date:** [Submission Date]

## Proposal Presentation Feedback

[To be filled after proposal presentation]

## Midterm Presentation Feedback

[To be filled after midterm presentation]
