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
