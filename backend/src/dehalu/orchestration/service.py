from __future__ import annotations

from sqlalchemy.orm import Session

from dehalu.adapters.language import build_language_registry
from dehalu.adapters.llm import ProviderRegistry
from dehalu.core.settings import Settings
from dehalu.orchestration.execution import build_execution_engine
from dehalu.schemas import NormalizedRequest, RepairOutcome, RunRequest, RunResponse
from dehalu.state.repository import RunRepository
from dehalu.verification.claims import ClaimExtractor
from dehalu.verification.policy import PolicyEngine
from dehalu.verification.sandbox import SandboxVerifier
from dehalu.verification.static_analysis import StaticAnalyzer


def normalize_request(request: RunRequest, settings: Settings) -> NormalizedRequest:
    language = (request.language_hint or _infer_language(request.prompt) or settings.default_language).lower()
    provider = request.provider or settings.default_provider
    return NormalizedRequest(
        prompt=request.prompt,
        language=language,
        risk_level=request.risk_level,
        latency_budget_seconds=request.latency_budget_seconds,
        provider=provider,
    )


def _infer_language(prompt: str) -> str | None:
    lowered = prompt.lower()
    if "python" in lowered or ".py" in lowered:
        return "python"
    return None


class RunOrchestrator:
    def __init__(self, settings: Settings, providers: ProviderRegistry) -> None:
        language_registry = build_language_registry()
        self.settings = settings
        self.providers = providers
        self.claim_extractor = ClaimExtractor(language_registry)
        self.static_analyzer = StaticAnalyzer(language_registry)
        self.sandbox_verifier = SandboxVerifier()
        self.policy_engine = PolicyEngine()
        self.execution_engine = build_execution_engine(
            settings.orchestration_mode,
            self.claim_extractor,
            self.static_analyzer,
            self.sandbox_verifier,
            self.policy_engine,
        )

    def run(self, request: RunRequest, session: Session) -> RunResponse:
        normalized = normalize_request(request, self.settings)
        provider = self.providers.get(normalized.provider)
        execution_result = self.execution_engine.execute(normalized, provider)
        repository = RunRepository(session)
        return repository.create_run(
            normalized_request=normalized,
            original_attempt=(
                execution_result.initial_attempt
                if execution_result.repair_result.outcome != RepairOutcome.skipped
                else None
            ),
            final_attempt=execution_result.final_attempt,
            repair_result=execution_result.repair_result,
        )
