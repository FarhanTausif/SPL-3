# Testing CrewAI Integration (Current, Runnable)

This guide only lists commands/flags that exist in this repository now.

## 1) Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[test]"
```

## 2) Core test commands

Run all backend tests:

```bash
pytest
```

Run CrewAI-focused suites:

```bash
pytest tests/unit/test_crewai_task_specs.py
pytest tests/integration/test_crewai_with_fake_provider.py
```

Run by marker:

```bash
pytest -m unit
pytest -m integration
pytest -m live_providers
```

## 3) Run the CrewAI workflow example (fake provider)

```bash
python scripts/example_crewai_workflow.py --workflow linear
python scripts/example_crewai_workflow.py --workflow repair
python scripts/example_crewai_workflow.py --workflow advanced
```

## 4) Live provider evaluation script

The repository includes:

```bash
python scripts/run_live_evaluation.py \
  --cases tests/evaluation/live_eval_cases.json \
  --output artifacts/evaluation/live_eval_report.json \
  --max-worker-polls 20
```

Supported CLI options are the ones implemented in the script:

- `--cases`
- `--output`
- `--max-worker-polls`

## 5) Environment variables used by current code

From `backend/src/dehalu/core/settings.py`:

- `DEHALU_DATABASE_URL`
- `DEHALU_ORCHESTRATION_MODE` (`direct` or `crewai`)
- `DEHALU_GEMINI_API_KEY`
- `DEHALU_GROQ_API_KEY`
- `DEHALU_MISTRAL_API_KEY`
- `DEHALU_CEREBRAS_API_KEY`
- `DEHALU_PROVIDER_LIVE_SMOKE_CHECKS_ENABLED`
- `DEHALU_PROVIDER_CAPTURE_FULL_PAYLOADS`
- `DEHALU_ROUTING_POLICY_VERSION`
- `DEHALU_PROMPT_POLICY_VERSION`

## 6) Important accuracy notes

- This repo currently does **not** define custom pytest flags like `--co-providers`, `--co-budget`, or `--co-timeout`.
- This repo currently does **not** include `.env.example.crewai`.
- Use `backend/.env.example` as the env template.

## 7) Pending work requiring e2e completion

The dedicated real-provider CrewAI e2e coverage task (`crewai-e2e-tests`) remains separate from this doc cleanup.
This guide is intentionally limited to commands and paths already present in the repository.
