# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DeHalu is a hallucination detection and mitigation system for CodeLLMs. It sits between a code-producing model and the final response, detecting hallucinated code artifacts and triggering correction only when needed. The system uses inference-time controls (prompt structure, multi-agent verification, deterministic parsing, sandbox execution) rather than model retraining.

## Build & Development Commands

### Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[test]"
```

### Running Tests

```bash
# All tests
pytest

# Focused tests
pytest tests/unit/test_orchestration_engines.py tests/integration/test_api.py

# With CrewAI workaround (if needed)
XDG_DATA_HOME=/tmp HOME="$PWD/.." pytest
```

### Database Migrations

```bash
alembic upgrade head
```

### Running the API

```bash
uvicorn dehalu.main:app --host 127.0.0.1 --port 8000 --reload
curl http://localhost:8000/health
```

### Running a Worker (for advanced/worker-backed mode)

```bash
python -m dehalu.worker
```

### Live Provider Evaluation

```bash
python scripts/run_live_evaluation.py \
  --cases tests/evaluation/live_eval_cases.json \
  --output artifacts/evaluation/live_eval_report.json
```

## Architecture Overview

### Layered Architecture

```
API Layer (FastAPI routes + Pydantic schemas)
    ↓
Orchestration Layer (RunOrchestrator, routing, worker coordination)
    ↓
Verification Pipeline (claims → static → sandbox → judges → policy)
    ↓
Adapter Layer (LLM providers, language adapters, tools)
    ↓
State Layer (SQLAlchemy models + repository pattern)
```

### Key Directories

- `backend/src/dehalu/api/` — FastAPI routes and dependencies
- `backend/src/dehalu/orchestration/` — Run lifecycle, routing, execution stages
- `backend/src/dehalu/verification/` — Multi-stage verification pipeline
  - `claims/` — Extract structured claims from generated code
  - `judges/` — Judge implementations (CoVe, etc.)
  - `static_analysis/` — Tree-sitter parsing, syntax/semantic checks
  - `sandbox/` — Bounded code execution
  - `policy/` — Aggregate evidence into decisions (accept/warn/repair/reject)
- `backend/src/dehalu/adapters/` — Provider adapters
  - `llm/` — Gemini, Groq, Mistral, Cerebras, Fake providers
  - `language/` — Language-specific parsing/execution
  - `tools/` — MCP and custom tool integrations
- `backend/src/dehalu/state/` — Database models, repository, ORM
- `backend/src/dehalu/schemas/` — Pydantic contracts
- `backend/src/dehalu/worker.py` — Async worker for advanced run mode

### Run Lifecycle States

`queued` → `started` → `completed` | `failed` | `needs_clarification`

### Verification + Mitigation Loop

```
Normalize → Generate → Verify → Policy → (Mitigate if repair_and_retry) → Re-verify → Return
```

Policy decisions: `accept`, `warn_and_return_partial`, `repair_and_retry`, `reject`

## Environment Configuration

Configure via `.env` or `DEHALU_*` environment variables:

```bash
DEHALU_DATABASE_URL=postgresql+psycopg://dehalu:dehalu@localhost:5432/dehalu
DEHALU_ORCHESTRATION_MODE=direct
DEHALU_GEMINI_API_KEY=...
DEHALU_GROQ_API_KEY=...
DEHALU_MISTRAL_API_KEY=...
DEHALU_CEREBRAS_API_KEY=...
DEHALU_PROVIDER_LIVE_SMOKE_CHECKS_ENABLED=true
DEHALU_ROUTING_POLICY_VERSION=v1
DEHALU_PROMPT_POLICY_VERSION=v1
```

See `backend/src/dehalu/core/settings.py` for all settings.

## Code Conventions

- **Python 3.12+** required (async/await, type hints mandatory)
- **Pydantic v2** for all API contracts
- **SQLAlchemy 2.x** for ORM
- **structlog** for structured logging
- **Async throughout** — no blocking I/O

### Import Order

```python
from __future__ import annotations

# Standard library
# Third-party
# Local (dehalu.*)
```

### Naming

- Classes: PascalCase (`RunOrchestrator`, `VerificationEvidence`)
- Functions: snake_case (`get_run_status()`)
- Tables: snake_case plural (`runs`, `evidence_records`)

## Key Design Patterns

- **Repository Pattern** — `RunRepository` abstracts database access
- **Adapter Pattern** — Provider adapters behind common interface
- **Worker Pattern** — Async workers claim runs from queue with leases
- **Evidence Tracking** — `VerificationEvidence` + `EventRecord` for audit trails
- **Dependency Injection** — FastAPI `Depends()` for request-scoped services

## Testing Strategy

- Unit tests in `tests/unit/` — isolated component tests
- Integration tests in `tests/integration/` — API + persistence tests
- Live evaluation in `scripts/run_live_evaluation.py` — tests against real providers

## Additional Resources

- `System_Architecture.md` — Detailed architecture and design rationale
- `System_Design.md` — Design decisions and trade-offs
- `backend/README.md` — Development runbook and troubleshooting
- `.github/copilot-instructions.md` — Additional context for AI assistants
- `.codex/AGENTS.md` — graphify knowledge graph usage rules
