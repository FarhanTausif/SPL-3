# DeHalu Project Runbook

This guide explains the repository layout and the local commands for running the database, backend, and frontend.

## Prerequisites

- Python 3.12+
- Node.js 18+
- npm
- PostgreSQL running locally for the default development database

The backend reads configuration from `backend/.env`. The frontend reads public browser configuration from `frontend/.env.local`.

## Repository Structure

```text
SPL-3/
├── backend/                         # FastAPI backend and verification/orchestration engine
│   ├── alembic/                     # Database migration environment
│   │   └── versions/                # Versioned migration files
│   ├── docs/                        # Backend-specific technical docs
│   ├── scripts/                     # Utility scripts and evaluation runners
│   ├── src/dehalu/                  # Backend Python package
│   │   ├── adapters/                # LLM, language, and tool adapters
│   │   ├── agents/                  # CrewAI-compatible agent definitions and workflow helpers
│   │   ├── api/                     # FastAPI route handlers and dependencies
│   │   ├── core/                    # App factory and settings
│   │   ├── orchestration/           # Run execution, routing, prompts, and service layer
│   │   ├── schemas/                 # Pydantic request/response contracts
│   │   ├── state/                   # SQLAlchemy database models, session, and repository
│   │   ├── telemetry/               # Logging setup
│   │   ├── verification/            # Claims, static analysis, sandbox, judges, and policy checks
│   │   ├── main.py                  # Uvicorn/FastAPI app entrypoint
│   │   └── worker.py                # Background worker for advanced runs
│   ├── tests/                       # Unit, integration, and evaluation tests
│   ├── .env.example                 # Backend environment template
│   ├── alembic.ini                  # Alembic configuration
│   └── pyproject.toml               # Backend dependencies and test config
├── frontend/                        # Next.js frontend
│   ├── app/                         # Next.js App Router pages and layouts
│   │   └── monitor/[id]/page.tsx    # Run monitoring page
│   ├── components/                  # React UI, workflow, and orchestration components
│   │   ├── orchestration/           # Run detail panels, timelines, flow visualization
│   │   ├── ui/                      # Reusable base UI components
│   │   └── workflow/                # Workflow DAG and agent/evidence panels
│   ├── hooks/                       # React hooks for polling, websocket updates, shortcuts
│   ├── lib/                         # API client, websocket client, utilities, theme, exports
│   ├── stores/                      # Zustand stores
│   ├── __tests__/                   # Frontend unit/component tests
│   ├── cypress/                     # End-to-end tests
│   ├── .env.local                   # Frontend local environment
│   └── package.json                 # Frontend scripts and dependencies
├── Papers/                          # Research/reference papers
├── graphify-out/                    # Generated graph analysis artifacts
└── *.md                             # Project planning, architecture, implementation, and audit docs
```

## Database Setup

The default backend database URL is:

```text
postgresql+psycopg://dehalu:dehalu@localhost:5432/dehalu
```

Create the local PostgreSQL user and database:

```bash
sudo -u postgres psql
```

Inside the PostgreSQL shell:

```sql
CREATE USER dehalu WITH PASSWORD 'dehalu';
CREATE DATABASE dehalu OWNER dehalu;
\q
```

From the backend folder, apply migrations:

```bash
cd backend
alembic upgrade head
```

If you only need a quick SQLite database for local testing, the repo includes a helper:

```bash
cd backend
python scripts/setup_test_db.py
```

Then set this in `backend/.env` while using SQLite:

```text
DEHALU_DATABASE_URL=sqlite:///./dehalu_test.db
```

## Backend Setup

From the repository root:

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[test]"
```

Create the backend environment file if it does not already exist:

```bash
cp .env.example .env
```

For normal local development, confirm these values in `backend/.env`:

```text
DEHALU_DATABASE_URL=postgresql+psycopg://dehalu:dehalu@localhost:5432/dehalu
DEHALU_APP_NAME=DeHalu Backend
DEHALU_ENVIRONMENT=development
DEHALU_ORCHESTRATION_MODE=crewai
DEHALU_DEFAULT_PROVIDER=auto
```

Live provider routing requires at least one provider API key:

```text
DEHALU_GEMINI_API_KEY=...
DEHALU_GROQ_API_KEY=...
DEHALU_MISTRAL_API_KEY=...
DEHALU_CEREBRAS_API_KEY=...
```

Run the backend API:

```bash
cd backend
source .venv/bin/activate
uvicorn dehalu.main:app --host 127.0.0.1 --port 8000 --reload
```

Verify the backend:

```bash
curl -sS http://127.0.0.1:8000/health
```

## Backend Worker

Advanced runs are worker-backed. Start the worker in a separate terminal:

```bash
cd backend
source .venv/bin/activate
python -m dehalu.worker
```

Use this when submitting `run_mode: "advanced"` from the frontend or API.

## Frontend Setup

From the repository root:

```bash
cd frontend
npm install
```

Create or verify `frontend/.env.local`:

```text
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
```

Run the frontend development server:

```bash
cd frontend
npm run dev
```

Open:

```text
http://localhost:3000
```

## Running The Full Project Locally

Use three terminals.

Terminal 1, backend API:

```bash
cd backend
source .venv/bin/activate
alembic upgrade head
uvicorn dehalu.main:app --host 127.0.0.1 --port 8000 --reload
```

Terminal 2, backend worker:

```bash
cd backend
source .venv/bin/activate
python -m dehalu.worker
```

Terminal 3, frontend:

```bash
cd frontend
npm run dev
```

Then visit:

```text
http://localhost:3000
```

## Useful API Checks

Health check:

```bash
curl -sS http://127.0.0.1:8000/health
```

Create a basic run:

```bash
curl -sS -X POST http://127.0.0.1:8000/v1/runs \
  -H "content-type: application/json" \
  -d '{"prompt":"Write Python code that computes a square root.","provider":"fake","run_mode":"basic"}'
```

Create an advanced worker-backed run:

```bash
curl -sS -X POST http://127.0.0.1:8000/v1/runs \
  -H "content-type: application/json" \
  -d '{"prompt":"Write Python code that computes a square root.","provider":"fake","run_mode":"advanced","acceptance_criteria":["Use math.sqrt."]}'
```

After receiving a `run_id`, inspect the run:

```bash
curl -sS http://127.0.0.1:8000/v1/runs/<run_id>
curl -sS http://127.0.0.1:8000/v1/runs/<run_id>/events
curl -sS http://127.0.0.1:8000/v1/runs/<run_id>/evidence
```

## Tests

Backend:

```bash
cd backend
source .venv/bin/activate
pytest
```

Frontend:

```bash
cd frontend
npm run test
```

End-to-end frontend tests:

```bash
cd frontend
npm run test:e2e
```

## Production Build Checks

Frontend production build:

```bash
cd frontend
npm run build
npm run start
```

Backend can be run without reload:

```bash
cd backend
source .venv/bin/activate
uvicorn dehalu.main:app --host 0.0.0.0 --port 8000
```

## Common Troubleshooting

- `alembic upgrade head` fails with a connection error: confirm PostgreSQL is running and `DEHALU_DATABASE_URL` matches the local database credentials.
- `/health` returns `degraded`: inspect the `providers` and `orchestration.provider_health_details` fields. Missing live provider keys are expected if you are using the `fake` provider locally.
- Advanced runs stay queued: start `python -m dehalu.worker` and re-check `/health` for worker readiness.
- Frontend cannot reach backend: confirm the API is running on port `8000` and `frontend/.env.local` points to `http://localhost:8000`.
- CORS errors: use `http://localhost:3000` or `http://127.0.0.1:3000`, which are allowed by the backend CORS configuration.
