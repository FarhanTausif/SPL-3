from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from dehalu.adapters.llm.base import LLMProvider
from dehalu.schemas import (
    CoderOutput,
    NormalizedRequest,
    RepairResult,
)
from dehalu.state.repository import EvaluationBundle


@dataclass(slots=True)
class CrewTaskDefinition:
    name: str
    description: str
    expected_output: str
    agent_role: str
    run: Callable[["CrewExecutionContext"], None]


@dataclass(slots=True)
class CrewExecutionContext:
    normalized_request: NormalizedRequest
    provider: LLMProvider
    generated_output: CoderOutput | None = None
    initial_attempt: EvaluationBundle | None = None
    final_attempt: EvaluationBundle | None = None
    repair_result: RepairResult | None = None
    notes: list[str] = field(default_factory=list)
