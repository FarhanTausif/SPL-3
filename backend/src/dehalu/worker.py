from __future__ import annotations

import time
from collections.abc import Callable
from datetime import datetime, timezone

from dehalu.adapters.llm import build_provider_registry
from dehalu.adapters.llm.runtime import ProviderExecutionError
from dehalu.core.settings import get_settings
from dehalu.orchestration import RunOrchestrator
from dehalu.schemas import StageStatus
from dehalu.state.database import SessionLocal
from dehalu.state.repository import RunRepository


class RunWorker:
    def __init__(
        self,
        *,
        settings=None,
        orchestrator: RunOrchestrator | None = None,
        session_factory: Callable[[], object] | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.providers = build_provider_registry(self.settings)
        self.orchestrator = orchestrator or RunOrchestrator(self.settings, self.providers)
        self.session_factory = session_factory or SessionLocal

    def run_once(self) -> bool:
        with self.session_factory() as session:
            repository = RunRepository(session)
            claimed = repository.claim_next_advanced_run(
                worker_id=self.settings.worker_id,
                lease_seconds=self.settings.worker_lease_seconds,
            )
            if claimed is None:
                return False
            try:
                self.orchestrator.process_claimed_run(claimed, session)
            except ProviderExecutionError as exc:  # pragma: no cover - exercised through integration behavior
                failure_message = (
                    f"Provider execution failed at stage '{exc.record.stage}' via '{exc.record.provider_name}' "
                    f"with failure kind '{exc.record.failure_kind.value}'."
                )
                stage_details = {
                    "worker_id": self.settings.worker_id,
                    "failure_stage": exc.record.stage,
                    "provider": exc.record.provider_name,
                    "failure_kind": exc.record.failure_kind.value,
                    "operator_hint": "Check provider credentials/connectivity and rerun worker.",
                    "provider_invocation": exc.record.model_dump(mode="json"),
                }
                repository.append_event(
                    claimed.id,
                    event_type="worker_provider_failure",
                    stage="worker",
                    status="failed",
                    message=failure_message,
                    payload=stage_details,
                )
                repository.fail_run(
                    claimed.id,
                    failure_message,
                    stage_summary=[
                        self._failure_stage(
                            "provider_failure",
                            {
                                **stage_details,
                                "error_message": str(exc),
                            },
                        )
                    ],
                )
            except Exception as exc:  # pragma: no cover - exercised through integration behavior
                failure_message = f"Worker execution failed with {type(exc).__name__}: {exc}"
                stage_details = {
                    "worker_id": self.settings.worker_id,
                    "error_type": type(exc).__name__,
                    "operator_hint": "Inspect worker logs and run events before retrying this run.",
                }
                repository.append_event(
                    claimed.id,
                    event_type="worker_runtime_failure",
                    stage="worker",
                    status="failed",
                    message=failure_message,
                    payload=stage_details,
                )
                repository.fail_run(
                    claimed.id,
                    failure_message,
                    stage_summary=[self._failure_stage("worker_failure", {**stage_details, "error_message": str(exc)})],
                )
            return True

    def run_forever(self) -> None:
        while True:
            processed = False
            for _ in range(self.settings.worker_batch_size):
                if not self.run_once():
                    break
                processed = True
            if not processed:
                time.sleep(self.settings.worker_poll_interval_seconds)

    def _failure_stage(self, stage: str, details: dict) -> StageStatus:
        now = datetime.now(timezone.utc)
        return StageStatus(stage=stage, status="failed", started_at=now, finished_at=now, details=details)


def main() -> None:
    RunWorker().run_forever()


if __name__ == "__main__":
    main()
