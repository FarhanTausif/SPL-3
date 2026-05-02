# Backend Development

## Local test entrypoint

Create a virtual environment, install the backend package with test extras, then run the test suite from `backend/`.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[test]"
pytest
```

Run a focused subset while iterating:

```bash
pytest tests/unit/test_orchestration_engines.py tests/integration/test_api.py
```

If `crewai` is installed in a Snap-backed environment, point its writable data home somewhere safe before running tests:

```bash
XDG_DATA_HOME=/tmp HOME="$PWD/.." pytest
```

## Optional CrewAI support

`crewai` is an optional runtime dependency for the internal orchestration path. The backend keeps a compatibility fallback when it is not installed, but operators can verify readiness through `GET /health`.

If you need the native CrewAI package in a local environment, install project dependencies from `pyproject.toml` inside the same virtual environment used for tests.

## Live provider runbook

Use this sequence to validate direct + worker-backed live-provider operation.

### 1) Configure `.env` (from `backend/`)

At least one live provider key must be set for live routing:

```bash
DEHALU_GEMINI_API_KEY=...
DEHALU_GROQ_API_KEY=...
DEHALU_MISTRAL_API_KEY=...
DEHALU_CEREBRAS_API_KEY=...
```

Recommended optional flags:

```bash
DEHALU_PROVIDER_LIVE_SMOKE_CHECKS_ENABLED=true
DEHALU_PROVIDER_CAPTURE_FULL_PAYLOADS=false
DEHALU_ROUTING_POLICY_VERSION=v1
DEHALU_PROMPT_POLICY_VERSION=v1
DEHALU_WORKER_ID=dehalu-worker-1
```

### 2) Start API and verify readiness

```bash
uvicorn dehalu.main:app --host 127.0.0.1 --port 8000 --reload
curl -sS http://127.0.0.1:8000/health
```

Check:
- `status`
- `orchestration.provider_role_readiness.live_provider_operation_ready`
- `orchestration.provider_health_details`
- `orchestration.worker_readiness` and `orchestration.queue_backlog`

### 3) Run direct basic API flow

```bash
curl -sS -X POST http://127.0.0.1:8000/v1/runs \
  -H "content-type: application/json" \
  -d '{"prompt":"Write Python code that computes a square root.","provider":"gemini","run_mode":"basic"}'
```

Expected: immediate terminal response (`status: "completed"` or policy terminal state) without worker involvement.

### 4) Run worker-backed advanced flow

Terminal A (worker):

```bash
python -m dehalu.worker
```

Terminal B (queue + poll):

```bash
curl -sS -X POST http://127.0.0.1:8000/v1/runs \
  -H "content-type: application/json" \
  -d '{"prompt":"Write Python code that computes a square root.","provider":"gemini","run_mode":"advanced","acceptance_criteria":["Use math.sqrt."]}'

curl -sS http://127.0.0.1:8000/v1/runs/<run_id>
curl -sS http://127.0.0.1:8000/v1/runs/<run_id>/events
curl -sS http://127.0.0.1:8000/v1/runs/<run_id>/evidence
```

Expected: initial `status: "queued"` then worker-driven transition to `completed`, `failed`, or `needs_clarification`.

### 5) Run live evaluation harness

```bash
python scripts/run_live_evaluation.py \
  --cases tests/evaluation/live_eval_cases.json \
  --output artifacts/evaluation/live_eval_report.json
```

## CrewAI docs and examples

- Agent/pipeline reference: `docs/CREWAI_AGENTS.md`
- Testing guide (current runnable commands only): `docs/TESTING_CREWAI_AGENTS.md`
- Fake-provider workflow example: `python scripts/example_crewai_workflow.py --workflow linear`

## Degraded states and troubleshooting

- Missing key for requested provider:
  - Symptom: provider is absent from `/health` live provider list; direct/advanced request with that provider returns HTTP 400 (`Provider '<name>' is unavailable...`).
  - Fix: set `DEHALU_<PROVIDER>_API_KEY`, restart API/worker.
- Smoke checks enabled and provider check fails:
  - Symptom: `/health` shows `provider_health_details.<provider>.live_smoke_check="failed"` and `ready_for_live_routing=false`; role readiness can drop to not ready.
  - Fix: verify key validity/network/provider status, retry; temporarily disable smoke checks only if you accept reduced readiness guarantees.
- Worker not processing advanced queue:
  - Symptom: `/health` shows `worker_readiness.state="missing"` or `"stale"` with backlog.
  - Fix: start/restart `python -m dehalu.worker`, confirm `worker_id` matches env, re-check `/health`.
- Top-level `status="degraded"`:
  - Means at least one registered provider failed health check. Inspect `providers` + `provider_health_details`, then rotate provider or fix credentials/connectivity.
