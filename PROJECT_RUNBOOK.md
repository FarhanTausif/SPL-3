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
npm i && npm run dev
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

Judge model defaults now use `gemini-3.8-flash`, `openai/gpt-oss-20b`, and `mistral-small-latest`. Existing `.env` values take precedence; update retired model names there. Provider catalog visibility does not guarantee generation quota or model access. These failures are shown explicitly in judge evidence and prevent unrestricted acceptance.

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

## Clarification, judge coverage, and entropy

Environment loading uses the repository location, independent of the launch directory. Process environment overrides `backend/.env`, which overrides the root `.env`. Restart both the API and worker after changing provider settings. The retired Groq `llama-3.1-8b-instant` configuration should use `openai/gpt-oss-20b`.

Clarification is limited to one round with at most three questions. Choose an option or enter a custom answer (custom text takes priority), then Continue. Run Anyway uses the current answers/defaults and bypasses more questions; verification still runs. Delegation such as “do it on your own” uses stated assumptions. Completed/bypassed clarification is persisted across worker restarts and browser reloads.

Provider status separates database/Ollama health from judge coverage. Configured credentials are unchecked until a real judge response is obtained. Refresh updates service/configuration status; it does not rerun historical judge calls. Rate limits, quota failures, timeouts, and model access failures remain explicit and prevent unrestricted acceptance.

Generation and repairs request Ollama token probabilities (`logprobs=true`, `top_logprobs=5`). Estimated token entropy is the mean entropy of returned top-token probabilities plus grouped remaining mass, normalized by `log(6)` for the score. It is a lower bound on full-distribution entropy, measured over the full generated response, including metadata. Raw nats, measured token coverage, and sampled-token log probabilities are retained. Unsupported/malformed measurements remain unavailable; old attempts are not backfilled. Metric definition is version 2.1.

The Metrics tab charts actual hallucination risk and MaHR across attempts. Both use a fixed 0–100% scale; risk is a comparative score rather than a calibrated error probability. Changes use percentage points and may decrease, stay flat, or increase.

Code view displays completed source artifacts and fenced source during streaming. Unfenced model prose and JSON metadata are excluded; generation explanations remain in saved evidence/export. Malformed generation/repair artifacts trigger one structured format recovery within the same attempt. A reset event replaces the invalid draft, and recovered code goes through the full verification pipeline. If recovery also fails, the run stops with an explicit error and retains completed attempts. Recovery entropy stays unavailable because it is not measured from the replacement response.
