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

## Optional CrewAI support

`crewai` is an optional runtime dependency for the internal orchestration path. The backend keeps a compatibility fallback when it is not installed, but operators can verify readiness through `GET /health`.

If you need the native CrewAI package in a local environment, install project dependencies from `pyproject.toml` inside the same virtual environment used for tests.
