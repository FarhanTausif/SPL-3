from __future__ import annotations

import time
from collections.abc import Callable

from dehalu.adapters.llm import build_provider_registry
from dehalu.core.settings import get_settings
from dehalu.orchestration import RunOrchestrator
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
            except Exception as exc:  # pragma: no cover - exercised through integration behavior
                repository.fail_run(claimed.id, str(exc))
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


def main() -> None:
    RunWorker().run_forever()


if __name__ == "__main__":
    main()
