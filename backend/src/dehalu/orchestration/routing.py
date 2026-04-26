from __future__ import annotations

from dataclasses import dataclass

from dehalu.adapters.llm import ProviderRegistry
from dehalu.adapters.llm.base import LLMProvider
from dehalu.schemas import JudgeResult


@dataclass(slots=True)
class ProviderRoleMatrix:
    clarification: tuple[str, ...] = ("gemini", "mistral")
    generation: tuple[str, ...] = ("grok", "gemini")
    judges: tuple[str, ...] = ("gemini", "mistral", "cerebras")
    cove: tuple[str, ...] = ("mistral", "gemini")


@dataclass(slots=True)
class RepairSelection:
    provider_name: str
    reason: str
    fallback_used: bool = False


class ProviderRouter:
    def __init__(self, providers: ProviderRegistry, matrix: ProviderRoleMatrix | None = None) -> None:
        self.providers = providers
        self.matrix = matrix or ProviderRoleMatrix()

    def get_clarification_provider(self) -> LLMProvider:
        return self._first_available(self.matrix.clarification)

    def get_generation_provider(self, requested_provider: str | None = None) -> LLMProvider:
        if requested_provider and requested_provider in self.providers.names() and requested_provider != "fake":
            return self.providers.get(requested_provider)
        return self._first_available(self.matrix.generation)

    def get_judge_providers(self) -> list[LLMProvider]:
        return self._available(self.matrix.judges)

    def get_cove_providers(self) -> list[LLMProvider]:
        return self._available(self.matrix.cove)

    def choose_repair_provider(
        self,
        *,
        judge_results: list[JudgeResult],
        generation_provider: LLMProvider,
    ) -> RepairSelection:
        scored = sorted(
            (
                (
                    self._repair_rank(result),
                    self._judge_precedence(result.provider),
                    result.provider,
                    result,
                )
                for result in judge_results
            ),
            reverse=True,
        )
        for _, _, provider_name, result in scored:
            if provider_name in self.providers.names():
                return RepairSelection(
                    provider_name=provider_name,
                    reason=f"Selected strongest verifier from panel: {provider_name} with verdict {result.verdict.value}.",
                    fallback_used=False,
                )
        return RepairSelection(
            provider_name=generation_provider.name,
            reason=f"Fell back to generation provider {generation_provider.name} because no selected verifier was available.",
            fallback_used=True,
        )

    def readiness(self) -> dict[str, object]:
        return {
            "clarification": self._readiness_for(self.matrix.clarification),
            "generation": self._readiness_for(self.matrix.generation),
            "judges": self._readiness_for(self.matrix.judges),
            "cove": self._readiness_for(self.matrix.cove),
        }

    def _first_available(self, names: tuple[str, ...]) -> LLMProvider:
        providers = self._available(names)
        if providers:
            return providers[0]
        if "fake" in self.providers.names():
            return self.providers.get("fake")
        raise ValueError(f"No configured provider available for route {names!r}.")

    def _available(self, names: tuple[str, ...]) -> list[LLMProvider]:
        available: list[LLMProvider] = []
        health = self.providers.health()
        for name in names:
            if name in self.providers.names() and health.get(name):
                available.append(self.providers.get(name))
        return available

    def _readiness_for(self, names: tuple[str, ...]) -> dict[str, object]:
        health = self.providers.health()
        available = [name for name in names if name in self.providers.names() and health.get(name)]
        return {"configured": list(names), "available": available, "ready": bool(available)}

    def _repair_rank(self, result: JudgeResult) -> tuple[int, float]:
        severity = {"fail": 2, "uncertain": 1, "pass": 0}[result.verdict.value]
        return severity, result.hallucination_score

    def _judge_precedence(self, provider_name: str) -> int:
        precedence = {"gemini": 1, "mistral": 2, "cerebras": 3, "grok": 0, "fake": -1}
        return precedence.get(provider_name, 0)
