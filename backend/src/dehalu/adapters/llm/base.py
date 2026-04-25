from __future__ import annotations

from typing import Protocol

from dehalu.schemas import CoderOutput, NormalizedRequest


class LLMProvider(Protocol):
    name: str

    def generate(self, request: NormalizedRequest) -> CoderOutput:
        raise NotImplementedError

    def judge(self, request: NormalizedRequest, output: CoderOutput) -> None:
        raise NotImplementedError("Judge support is deferred to a later backend iteration.")

    def repair(self, request: NormalizedRequest, output: CoderOutput) -> None:
        raise NotImplementedError("Repair support is deferred to a later backend iteration.")

    def healthcheck(self) -> bool:
        raise NotImplementedError

