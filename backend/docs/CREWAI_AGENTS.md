# DeHalu CrewAI Pipeline (Current State)

This document reflects the code that exists today under `backend/src/dehalu/agents/`.

## What exists

- Task specs: `backend/src/dehalu/agents/task_specs.py`
  - `create_all_task_specs(stages)` builds 9 task specs:
    - `ClarificationTask`
    - `GenerationTask`
    - `ClaimExtractionTask`
    - `StaticAnalysisTask`
    - `SandboxExecutionTask`
    - `JudgeTask`
    - `CoVeTask`
    - `PolicyCoordinatorTask`
    - `RepairTask`
- Workflow graph/executor: `backend/src/dehalu/agents/workflow.py`
  - `build_linear_workflow(task_specs)`
  - `build_repair_aware_workflow(task_specs)`
  - `build_direct_execution_workflow(task_specs)`
  - `build_advanced_execution_workflow(task_specs)`
  - `WorkflowExecutor(workflow=..., runner=..., context=...)`
- Runner: `backend/src/dehalu/agents/runner.py` (`CrewAIRunner`)

## Execution behavior

- Linear flow: clarification (conditional) → generation → claims/static/sandbox → judge/cove → policy
- Repair-aware flow: linear flow + conditional `RepairTask`, then re-verification
- Repair is bounded to one retry in the workflow logic.

## Minimal local check (fake provider)

From `backend/`:

```bash
python scripts/example_crewai_workflow.py --workflow linear
python scripts/example_crewai_workflow.py --workflow repair
```

This script uses `FakeLLMProvider`, builds task specs/workflow, executes the workflow, and prints trace/policy output.

## API/worker entrypoints

```bash
uvicorn dehalu.main:app --host 127.0.0.1 --port 8000 --reload
python -m dehalu.worker
```

## Notes

- CrewAI package support is optional at runtime (`dehalu.agents.compat`).
- The orchestration mode is controlled by `DEHALU_ORCHESTRATION_MODE` (`direct` or `crewai`).
