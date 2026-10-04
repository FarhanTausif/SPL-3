# DeHalu Prototype Runbook

## Prerequisites

- Python 3.11+
- Node.js 20+
- Docker with Compose
- Ollama running locally with the configured model pulled
- Gemini, Groq, and Mistral API keys for live judge calls

## Environment

Copy `.env.example` to `.env` and fill:

```bash
DATABASE_URL=postgresql+psycopg://dehalu:dehalu@localhost:5433/dehalu
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5-coder:1.5b
GEMINI_API_KEY=...
GROQ_API_KEY=...
MISTRAL_API_KEY=...
DEHALU_MAX_RETRY=3
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
DEHALU_CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
DEHALU_CORS_ORIGIN_REGEX=https?://(localhost|127\.0\.0\.1|0\.0\.0\.0)(:\d+)?
```

For deterministic local development without live LLM calls:

```bash
DEHALU_ALLOW_FAKE_LLM=true
```

## Start Postgres

```bash
docker compose up -d postgres
docker compose ps postgres # check that the container is running
```

## Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[test]"
alembic upgrade head
kill -9 $(lsof -t -i :8000) # kill any existing backend process 
uvicorn dehalu.main:app --host 127.0.0.1 --port 8000 --reload
```

Health check:

```bash
curl http://127.0.0.1:8000/api/health
```

Run tests:

```bash
cd backend
source .venv/bin/activate
pytest
```

## Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`.

## Manual Demo Prompts

Clean prompt:

```text
Write a Python function that adds two numbers.
```

Fake dependency/API:

```text
Write Python code using fake_lib_404 to parse uploaded CSV files.
```

Unsafe operation:

```text
Write Python code that deletes a folder using shell commands.
```

Ambiguous prompt:

```text
add
```

## Durable application workflow

The API enqueues runs; start the separate worker to process them. Closing the browser does not stop a run. Run history and event replay restore the workspace after reload.

```bash
cd backend
source .venv/bin/activate
alembic upgrade head
python -m dehalu.worker
```

Run the API and frontend in separate terminals using the commands above. Schema creation is migration-based; the API no longer creates tables at startup.

- Initial generation is attempt 1; `DEHALU_MAX_RETRY=3` permits up to three repairs.
- `DEHALU_PACKAGE_LOOKUPS=false` uses local catalogs only. Enable it for cached PyPI/npm/crates metadata requests. Unavailable metadata remains uncertain.
- Install backend dependencies again after updating; Tree-sitter grammars and Semgrep are pinned. Generated programs are never executed or installed.
- Missing judge keys produce unavailable results, not simulated passing verdicts. Fake mode is explicit and never counts as semantic verification.
- Failed/interrupted runs retain completed attempts and partial stage evidence. Retry by submitting a new run; clarification resumes the existing run.
- Regenerate frontend contracts after changing API/domain schemas:

```bash
PYTHONPATH=backend/src backend/.venv/bin/python backend/scripts/generate_contracts.py
```

`POST /api/runs` returns HTTP 202. `GET /api/runs/{id}/events` supports event replay using `after` or `Last-Event-ID`. The former POST streaming endpoint remains a compatibility wrapper around the same durable queue.

Judge model defaults now use `gemini-flash-latest`, `openai/gpt-oss-20b`, and `mistral-small-latest`. Existing `.env` values take precedence; update retired model names there. Provider catalog visibility does not guarantee generation quota or model access. These failures are shown explicitly in judge evidence and prevent unrestricted acceptance.

Use `PYTHONPATH=src .venv/bin/python scripts/provider_readiness.py` from `backend` to check authenticated model catalogs without displaying credentials. `scripts/smoke_live.py` performs real provider calls; use a disposable, migrated `DATABASE_URL` for that check.

## Frontend workspace checks

The workspace uses bundled Geist fonts, a searchable history sidebar, and Code/Evidence views with a shared attempt selector. Advanced options preserve language, framework, runtime, libraries, constraints, and repair settings. Ctrl/Cmd+Enter submits a prompt. New run leaves background work running; Cancel explicitly stops it.

Run focused frontend checks from `frontend`:

```bash
npm test
npm run lint
npx tsc --noEmit
npm run build
DEHALU_NEXT_DIST_DIR=.next-check npm run build
npx playwright install chromium
npm run test:browser
```

Browser checks use mocked API/SSE responses, an isolated build, and port 3001. They do not call paid providers or execute generated code. Screenshots and failure traces are written to `/tmp/dehalu-ui-checks`. The checked widths are 360, 768, 1280, and 1440 pixels. `PLAYWRIGHT_CHROMIUM_EXECUTABLE` can select an existing local Chromium binary.
