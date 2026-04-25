from __future__ import annotations

from typing import Protocol

from dehalu.schemas import (
    CoderOutput,
    CoVeResult,
    ExtractedClaim,
    JudgeResult,
    NormalizedRequest,
    SandboxResult,
    StaticFinding,
)


class LLMProvider(Protocol):
    name: str

    def generate(self, request: NormalizedRequest) -> CoderOutput:
        raise NotImplementedError

    def judge(
        self,
        request: NormalizedRequest,
        output: CoderOutput,
        claims: list[ExtractedClaim],
        static_findings: list[StaticFinding],
        sandbox_result: SandboxResult,
    ) -> JudgeResult:
        raise NotImplementedError("Judge support is deferred to a later backend iteration.")

    def cove(
        self,
        request: NormalizedRequest,
        output: CoderOutput,
        claims: list[ExtractedClaim],
        static_findings: list[StaticFinding],
        sandbox_result: SandboxResult,
        judge_result: JudgeResult,
    ) -> CoVeResult:
        raise NotImplementedError("CoVe support is deferred to a later backend iteration.")

    def repair(self, request: NormalizedRequest, output: CoderOutput) -> None:
        raise NotImplementedError("Repair support is deferred to a later backend iteration.")

    def healthcheck(self) -> bool:
        raise NotImplementedError
