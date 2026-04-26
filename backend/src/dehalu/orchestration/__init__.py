from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dehalu.orchestration.service import RunOrchestrator, normalize_request

__all__ = ["RunOrchestrator", "normalize_request"]


def __getattr__(name: str):
    if name in __all__:
        from dehalu.orchestration.service import RunOrchestrator, normalize_request

        exports = {
            "RunOrchestrator": RunOrchestrator,
            "normalize_request": normalize_request,
        }
        return exports[name]
    raise AttributeError(name)
