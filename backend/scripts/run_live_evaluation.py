from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from dehalu.adapters.llm import build_provider_registry
from dehalu.core.settings import get_settings
from dehalu.orchestration import RunOrchestrator
from dehalu.schemas import RunLifecycleStatus, RunRequest
from dehalu.state.database import SessionLocal
from dehalu.state.repository import RunRepository
from dehalu.worker import RunWorker


def load_cases(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def terminal(status: RunLifecycleStatus) -> bool:
    return status in {
        RunLifecycleStatus.completed,
        RunLifecycleStatus.failed,
        RunLifecycleStatus.needs_clarification,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run live advanced evaluations against configured cloud providers.")
    parser.add_argument(
        "--cases",
        default="tests/evaluation/live_eval_cases.json",
        help="Path to the evaluation case file, relative to backend/ unless absolute.",
    )
    parser.add_argument(
        "--output",
        default="artifacts/evaluation/live_eval_report.json",
        help="Path to write the evaluation report, relative to backend/ unless absolute.",
    )
    parser.add_argument(
        "--max-worker-polls",
        type=int,
        default=20,
        help="Maximum worker polling iterations per case.",
    )
    args = parser.parse_args()

    backend_root = Path(__file__).resolve().parents[1]
    case_path = Path(args.cases)
    output_path = Path(args.output)
    if not case_path.is_absolute():
        case_path = backend_root / case_path
    if not output_path.is_absolute():
        output_path = backend_root / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)

    settings = get_settings()
    providers = build_provider_registry(settings)
    orchestrator = RunOrchestrator(settings, providers)
    worker = RunWorker(settings=settings, orchestrator=orchestrator, session_factory=SessionLocal)

    cases = load_cases(case_path)
    provider_stats: dict[str, Counter] = defaultdict(Counter)
    results: list[dict] = []

    for case in cases:
        with SessionLocal() as session:
            request = RunRequest(
                prompt=case["prompt"],
                provider=case.get("provider"),
                risk_level=case.get("risk_level", "medium"),
                run_mode="advanced",
                acceptance_criteria=case.get("acceptance_criteria", []),
            )
            created = orchestrator.run(request, session)
            polls = 0
            while polls < args.max_worker_polls:
                detail = orchestrator.get_run_detail(created.run_id, session)
                if terminal(detail.status):
                    break
                worker.run_once()
                polls += 1
            repository = RunRepository(session)
            detail = repository.get_run_detail(created.run_id)
            evidence = repository.get_run_evidence(created.run_id)
            provider_evidence = next((item for item in evidence if item.kind == "provider_invocation"), None)
            routing_evidence = next((item for item in evidence if item.kind == "routing"), None)
            provider_name = detail.normalized_request.provider
            provider_stats[provider_name]["runs"] += 1
            provider_stats[provider_name][detail.status.value] += 1
            if detail.policy_decision is not None:
                provider_stats[provider_name][detail.policy_decision.state.value] += 1
            results.append(
                {
                    "case_id": case["id"],
                    "expected_outcome": case.get("expected_outcome"),
                    "run_id": created.run_id,
                    "status": detail.status.value,
                    "policy_state": detail.policy_decision.state.value if detail.policy_decision else None,
                    "fused_metrics": detail.fused_metrics.model_dump(mode="json") if detail.fused_metrics else None,
                    "provider_invocation_count": provider_evidence.payload.get("count", 0) if provider_evidence else 0,
                    "routing": routing_evidence.payload if routing_evidence else {},
                    "evidence_summary": detail.evidence_summary,
                }
            )

    report = {
        "routing_policy_version": settings.routing_policy_version,
        "prompt_policy_version": settings.prompt_policy_version,
        "provider_summary": {provider: dict(counter) for provider, counter in provider_stats.items()},
        "results": results,
    }
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
