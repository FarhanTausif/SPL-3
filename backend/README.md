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

## Live provider evaluation

The advanced worker-backed pipeline can be exercised against live Gemini, Grok, Mistral, and Cerebras credentials with the bundled evaluation harness. This runs the real advanced queue path, polls the worker, and writes a compact report with routing and provider-invocation evidence.

From `backend/`:

```bash
python scripts/run_live_evaluation.py \
  --cases tests/evaluation/live_eval_cases.json \
  --output artifacts/evaluation/live_eval_report.json
```

Useful environment flags:

- `DEHALU_PROVIDER_LIVE_SMOKE_CHECKS_ENABLED=true`
- `DEHALU_PROVIDER_CAPTURE_FULL_PAYLOADS=true`
- `DEHALU_ROUTING_POLICY_VERSION=v1`
- `DEHALU_PROMPT_POLICY_VERSION=v1`

`GET /health` now reports provider role readiness, provider health details, worker freshness, and the advanced-run queue backlog so operators can verify that live evaluation is actually runnable before submitting cases.
