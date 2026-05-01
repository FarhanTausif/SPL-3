# Copilot Instructions for SPL-3 Repository

## Project Overview

DeHalu is a hallucination detection and mitigation system for CodeLLMs. It sits between a code-producing model and the final response, detecting hallucinated code artifacts and triggering correction only when needed. The system uses inference-time controls (prompt structure, multi-agent verification, deterministic parsing, sandbox execution) rather than model retraining.

**Key Features:**
- Multi-provider LLM verification gateway (Gemini, Groq, Mistral, Cerebras)
- Multi-stage code verification pipeline (claims → static → sandbox → judges → policy)
- Worker-backed asynchronous orchestration
- Evidence-based claim extraction and analysis
- Deterministic verification + LLM-as-a-Judge consensus

**Research Context:**
This implementation is grounded in systematic research on code hallucinations, including chain-of-thought analysis, metamorphic testing, and hallucination taxonomy (see `Papers/` and `System_Design.md`).

## Project Structure

```
SPL-3/
├── Papers/                    # Research papers on LLM hallucinations
├── backend/                   # DeHalu verification gateway (Python FastAPI)
│   ├── src/dehalu/
│   │   ├── api/              # FastAPI routes and dependencies
│   │   ├── core/             # App initialization, settings, configuration
│   │   ├── orchestration/    # Async run coordination and routing
│   │   ├── verification/     # Multi-stage verification pipeline
│   │   │   ├── claims/       # Claim extraction from generated code
│   │   │   ├── judges/       # Judge implementations (CoVe, etc.)
│   │   │   ├── policy/       # Policy decision engine
│   │   │   ├── sandbox/      # Code execution sandbox
│   │   │   └── static_analysis/  # Static code analysis
│   │   ├── adapters/         # Provider adapters (LLM, language, tools)
│   │   ├── state/            # Database models, repository, ORM
│   │   ├── schemas/          # Pydantic data contracts
│   │   ├── telemetry/        # Logging and observability
│   │   └── agents/           # CrewAI agents (optional)
│   ├── tests/                # pytest test suite
│   ├── scripts/              # Utility scripts (live evaluation)
│   ├── alembic/              # Database migrations
│   └── pyproject.toml        # Python dependencies and build config
├── graphify-out/             # Knowledge graph analysis output
└── venv/                     # Python virtual environment
```

## Backend Stack & Patterns

### Core Technologies

| Component | Technology | Version |
|-----------|-----------|---------|
| Web Framework | FastAPI | ≥0.115 |
| ORM | SQLAlchemy | ≥2.0 |
| Database | PostgreSQL | psycopg[binary] ≥3.2 |
| Async Worker | Built-in (async/await) | Python 3.12+ |
| Optional Orchestration | CrewAI | ≥1.14.1 |
| Settings | Pydantic-settings | ≥2.4 |
| Logging | structlog | ≥24.1 |
| Testing | pytest | ≥8.2 |
| Migrations | Alembic | ≥1.13 |

### Core Architecture Principles

**Layered Architecture:**
1. **API Layer** (`api/`) - FastAPI routes + Pydantic request/response schemas
2. **Orchestration Layer** (`orchestration/`) - RunOrchestrator manages run lifecycle and routing
3. **Verification Pipeline** (`verification/`) - Multi-stage verification (claims → static → sandbox → judges → policy)
4. **Adapter Layer** (`adapters/`) - Pluggable providers (LLM, languages, execution tools)
5. **State Layer** (`state/`) - SQLAlchemy models + repository pattern for data access
6. **Telemetry Layer** (`telemetry/`) - structlog for JSON-structured logging

**Key Design Patterns:**
- **Dependency Injection** - FastAPI Depends() for request-scoped services
- **Repository Pattern** - RunRepository abstracts database access
- **Adapter Pattern** - Provider adapters (LLM, language execution)
- **Worker Pattern** - Async workers claim runs from queue with time-based leases
- **Evidence Tracking** - VerificationEvidence + EventRecord for audit trails
- **Role-Based Routing** - Providers mapped to roles (clarification, generation, judge, cove, repair)

### Environment Configuration

Configure via `DEHALU_*` prefixed environment variables:

```bash
# Database
DEHALU_DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/dehalu

# Execution Mode
DEHALU_ORCHESTRATION_MODE=direct  # Options: direct, crewai

# Provider Configuration
DEHALU_GEMINI_API_KEY=<key>
DEHALU_GEMINI_BASE_URL=https://generativelanguage.googleapis.com
DEHALU_GROQ_API_KEY=<key>
DEHALU_MISTRAL_API_KEY=<key>
DEHALU_CEREBRAS_API_KEY=<key>

# Policy Versions
DEHALU_ROUTING_POLICY_VERSION=v1
DEHALU_PROMPT_POLICY_VERSION=v1

# Observability
DEHALU_PROVIDER_LIVE_SMOKE_CHECKS_ENABLED=false
DEHALU_PROVIDER_CAPTURE_FULL_PAYLOADS=false
```

**Provider Selection:**
- If real provider keys present → routes prioritize real provider
- If no keys present → falls back to `fake` provider (testing)
- Each provider can fail independently; routing tries next candidate in role chain

## Build, Test & Development

### Local Development Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac; on Windows: .venv\Scripts\activate
pip install -e ".[test]"
```

### Running Tests

```bash
# All tests (from backend/ directory)
pytest

# Focused tests
pytest tests/unit/test_orchestration_engines.py tests/integration/test_api.py

# With custom environment (CrewAI workaround on some systems)
XDG_DATA_HOME=/tmp HOME="$PWD/.." pytest
```

### Database Setup

```bash
# Apply migrations (Alembic manages schema)
alembic upgrade head

# Reset database (development only)
alembic downgrade base
alembic upgrade head
```

### Running the Server

```bash
# Ensure .env is configured with DEHALU_DATABASE_URL and provider keys
uvicorn dehalu.core.app:app --reload --host 0.0.0.0 --port 8000
```

### Live Provider Testing

```bash
# Test against live cloud providers (requires valid API keys in .env)
python scripts/run_live_evaluation.py \
  --cases tests/evaluation/live_eval_cases.json \
  --output artifacts/evaluation/live_eval_report.json

# Environment flags for evaluation:
export DEHALU_PROVIDER_LIVE_SMOKE_CHECKS_ENABLED=true
export DEHALU_PROVIDER_CAPTURE_FULL_PAYLOADS=true
```

### Health Check

```bash
curl http://localhost:8000/health
```

Returns provider availability, worker freshness, queue stats, and policy versions.

## Testing Strategy

### Unit Tests
- Located in `tests/unit/`
- Test individual components in isolation (settings, adapters, repository)
- Marker: `@pytest.mark.unit`
- Run with: `pytest -m unit`

### Integration Tests
- Located in `tests/integration/`
- Test API routes, orchestration flow, multi-provider routing
- Marker: `@pytest.mark.integration`
- Run with: `pytest -m integration`

### Live Provider Tests (Optional)
- Located in `tests/evaluation/`
- Test against real cloud providers (Gemini, Groq, Mistral, Cerebras)
- Requires valid API keys in `.env`
- Run with: `python scripts/run_live_evaluation.py`
- Marker: `@pytest.mark.live_providers`

### Test Coverage Targets
- Core orchestration paths: Direct + worker-backed execution
- Provider fallback chains and error handling
- Database state transitions and evidence collection
- Verification pipeline stages (claims, static, sandbox, judge, policy)

## Code Style & Conventions

### Python Standards

- **Python 3.12+** required (async/await, type hints, pydantic 2.x)
- **Type hints** mandatory on all functions (use `from __future__ import annotations`)
- **Pydantic models** for all API contracts (request/response validation at boundaries)
- **Structured logging** via structlog (JSON output, always include context)
- **Async/await** throughout (no blocking I/O; use `httpx.AsyncClient`, not `requests`)
- **Comments** only where logic is non-obvious; let code explain intent

### Import Organization

```python
from __future__ import annotations  # Always first

# Standard library
from datetime import datetime
from typing import Any

# Third-party
from fastapi import FastAPI, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

# Local
from dehalu.core.settings import Settings
from dehalu.state.repository import RunRepository
```

### Naming Conventions

- **Classes**: PascalCase (e.g., `RunOrchestrator`, `VerificationEvidence`)
- **Functions/Methods**: snake_case (e.g., `get_run_status()`, `_internal_helper()`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `MAX_RETRY_ATTEMPTS`, `DEFAULT_TIMEOUT_SECONDS`)
- **Database Tables**: snake_case, plural (e.g., `runs`, `evidence_records`, `worker_heartbeats`)
- **Pydantic Models**: PascalCase + suffix (e.g., `RunRequest`, `RunResponse`, `VerificationPolicySetting`)
- **Private Methods/Attrs**: Leading underscore (e.g., `_internal_routing_logic()`)

### File Organization

- **`routes.py`** - FastAPI APIRouter and endpoint handlers
- **`models.py`** - SQLAlchemy ORM models
- **`contracts.py`** or **`schemas.py`** - Pydantic request/response schemas
- **`repository.py`** - Data access layer (query builders, session management)
- **`registry.py`** - Factory/registry patterns for provider/tool instantiation
- **`service.py`** - Business logic and orchestration
- **`__init__.py`** - Module exports and public API

### Database Conventions

- All schema changes via Alembic migrations (`alembic/versions/`)
- ORM models inherit from `Base` (declarative session)
- Use `@validates` for field-level validation; put complex logic in SQLAlchemy events or repository
- Always use context managers for session management: `with session_factory() as session: ...`

## Verification Pipeline

**Standard verification flow (all runs):**
1. **Claim Extraction** - Extract function/API claims from generated code (`claims/`)
2. **Static Analysis** - Syntax, type, import checks (`static_analysis/`)
3. **Sandbox Execution** - Safe execution with resource limits (`sandbox/`)
4. **Judge Evaluation** - LLM-based verdict (CoVe, other judges) (`judges/`)
5. **Policy Decision** - Aggregate evidence into final decision (accept/warn/reject) (`policy/`)
6. **Mitigation** (if triggered) - Repair attempt + re-verify (up to N retries)
7. **Evidence Recording** - Persist all findings in database

**Pipeline Schemas:**
- `ExtractedClaim` - Parsed claim from code
- `StaticFinding` - Static analysis result (type error, import missing, etc.)
- `SandboxResult` - Execution result (output, error, duration)
- `JudgeFinding` + `JudgeResult` - Judge verdict (CoVe score, reasoning)
- `VerificationEvidence` - Final aggregated evidence + decision
- `FailureContext` - Context for mitigation trigger (what failed, why)
- `RepairAttempt` - Repair result (fixer output, success/failure)

**Policy Engine:**
- Aggregates evidence from all stages
- Applies policy rules (thresholds, hard-fail conditions)
- Decides: accept (low hallucination), warn (medium, needs review), reject (high/critical)
- Triggers mitigation on specific conditions (failed execution, import errors, judge consensus)

## Important Notes

- **Async throughout** - No blocking I/O; use `httpx.AsyncClient` for external APIs
- **Pydantic validation** - Always validate at boundaries (API routes, worker input, database reads)
- **Database transactions** - Use SQLAlchemy session context managers; don't leave sessions open
- **CrewAI is optional** - Backend works without it; check `HAS_CREWAI` flag before using CrewAI features
- **Provider credentials** - Always via environment variables (`DEHALU_*`), never hardcoded or in source
- **Health checks required** - Validate provider readiness before queuing; check `/health` endpoint
- **Worker leasing** - Workers renew leases via heartbeats; stale workers (no heartbeat for 2x lease duration) are dropped
- **Error classification** - Map provider errors to HTTP status codes (400 = config/invalid input, 503 = unavailable)
- **Evidence persistence** - Always record verification steps in database for audit trail

## Relevant Tools & Skills

### For Backend Development

- **FastAPI debugging** - Use async-aware debuggers (`pdb` with asyncio support, or IDE debugger)
- **SQLAlchemy query analysis** - Profile queries, detect N+1 problems, use `.options(joinedload())` for optimization
- **Database migration review** - Analyze `alembic/versions/` for schema evolution and backward compatibility
- **pytest parametrization** - Understand fixtures, marks (`@pytest.mark.unit`, `@pytest.mark.live_providers`), async test support
- **Multi-provider routing** - Test failover logic, verify provider availability checks, simulate provider failures
- **Performance profiling** - Use async profilers for I/O-heavy paths; monitor worker queue depth and claim latency

### For Research & Documentation

- **graphify** - Generates knowledge graphs from codebase; use to trace dependencies across modules
- **Literature correlation** - Link backend implementation decisions to research papers in `Papers/` directory
- **Architecture diagrams** - Use for documenting component flow and evidence flow through pipeline

### Recommended Custom Agents (for future use)

1. **live-provider-validator** - Smoke test against real cloud providers, validate config, check API quotas
2. **crewai-agent-generator** - Auto-generate CrewAI agent definitions from component specs
3. **db-migration-reviewer** - Analyze Alembic migrations, detect backward compatibility issues
4. **performance-profiler** - Profile backend execution, identify bottlenecks in verification pipeline
5. **evidence-auditor** - Validate evidence collection and database consistency after runs

## Development Workflow

1. **Environment First** - Set up `.env` with `DEHALU_DATABASE_URL` and provider keys; verify with `/health`
2. **Schema First** - Define Pydantic contracts in `schemas/contracts.py` before implementation
3. **Tests First** - Write unit/integration tests in `tests/` before implementing business logic
4. **Implementation** - Implement against tests using repository + service pattern
5. **Database Migrations** - Generate Alembic migration if schema changes; test rollback
6. **Integration** - Run full pipeline tests; verify orchestration paths (direct + worker)
7. **Live Validation** - Test against actual providers via evaluation script (if available)

## graphify

This project has a graphify knowledge graph at graphify-out/.

Rules:
- Before answering architecture or codebase questions, read graphify-out/GRAPH_REPORT.md for god nodes and community structure
- If graphify-out/wiki/index.md exists, navigate it instead of reading raw files
- For cross-module "how does X relate to Y" questions, prefer `graphify query "<question>"`, `graphify path "<A>" "<B>"`, or `graphify explain "<concept>"` over grep — these traverse the graph's EXTRACTED + INFERRED edges instead of scanning files
- After modifying code files in this session, run `graphify update .` to keep the graph current (AST-only, no API cost)

## References

- **System Architecture**: See `System_Architecture.md` for component diagrams and layer responsibilities
- **System Design**: See `System_Design.md` for design decisions, verification pipeline semantics, and mitigation flow
- **Mitigation Design**: See `MITIGATION_PIPELINE_HIGH_LEVEL_DESIGN.md` for hallucination detection and repair strategy
- **API Routes**: See `backend/src/dehalu/api/routes.py` for endpoint definitions and request/response contracts
- **Database Models**: See `backend/src/dehalu/state/models.py` for RunRecord, EvidenceRecord, and event tracking
- **Health Endpoint**: GET `/health` returns provider availability, worker freshness, queue backlog, and policy versions

---

*Last updated: 2025-01-01 (Backend production-ready, real-provider support enabled)*