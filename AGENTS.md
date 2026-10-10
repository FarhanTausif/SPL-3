# Repository Guidelines

## Project Structure & Module Organization

DeHalu is split into a FastAPI backend and a Next.js frontend. Backend source lives in `backend/src/dehalu`, with API routes in `api/`, orchestration in `services/`, persistence in `state/`, and hallucination checks in `verification/`. Backend tests are under `backend/tests/unit` and `backend/tests/integration`; Alembic migrations live in `backend/alembic`. Frontend routes are in `frontend/app`, shared UI in `frontend/components`, client utilities in `frontend/lib`, and shadcn/ui primitives in `frontend/components/ui`. Docs and academic artifacts are in `PROJECT_RUNBOOK.md`, `SRS/`, and `Papers/`.

## Implementation High Level Design
High level design is documented in `High_Level_Design.md`.

## Build, Test, and Development Commands

- `docker compose up -d postgres`: start the local PostgreSQL service on port `5433`.
- `cd backend && python3 -m venv .venv && source .venv/bin/activate`: create the Python environment.
- `cd backend && pip install -e ".[test]"`: install backend runtime and test dependencies.
- `cd backend && alembic upgrade head`: apply database migrations.
- `cd backend && uvicorn dehalu.main:app --host 127.0.0.1 --port 8000 --reload`: run the API locally.
- `cd backend && pytest`: run backend unit and integration tests.
- `cd frontend && npm install`: install frontend dependencies.
- `cd frontend && npm run dev`: run the Next.js app at `http://localhost:3000`.
- `cd frontend && npm run build`, `npm run lint`, `npm test`: build, lint, and run Vitest.

## Coding Style & Naming Conventions

Use Python 3.11+ with typed Pydantic/FastAPI interfaces and clear module boundaries. Python files use `snake_case`; classes and schemas use `PascalCase`; route handlers should return declared response models where practical. Frontend code uses TypeScript, React function components, `PascalCase` component files, and aliases such as `@/components/ui/button`. Keep Tailwind classes readable and colocated with components.

## Testing Guidelines

Backend tests use `pytest` and `pytest-asyncio`; name files `test_*.py` and place contract-level coverage in `backend/tests/integration`. Frontend tests use Vitest with `*.test.ts` or `*.test.tsx` naming. Add focused tests for changed behavior, especially API contracts, streaming events, verification policy, and client parsing.

## Commit & Pull Request Guidelines

Git history follows Conventional Commit prefixes such as `feat:`, `chore:`, and `docs:`. Keep commits small and imperative, for example `feat: add streaming verification backend`. Pull requests should describe the user-visible change, list verification commands run, call out configuration or migration changes, and include screenshots for UI changes.

## Security & Configuration Tips

Copy `.env.example` to `.env` and keep secrets local. Use `DEHALU_ALLOW_FAKE_LLM=true` for deterministic development without live provider calls. Do not commit API keys, database dumps, virtual environments, `.next`, or other generated artifacts.
