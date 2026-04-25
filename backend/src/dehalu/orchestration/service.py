from __future__ import annotations

from sqlalchemy.orm import Session

from dehalu.adapters.language import build_language_registry
from dehalu.adapters.llm import ProviderRegistry
from dehalu.core.settings import Settings
from dehalu.schemas import NormalizedRequest, RunRequest, RunResponse
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

    def run(self, request: RunRequest, session: Session) -> RunResponse:
        normalized = normalize_request(request, self.settings)
        provider = self.providers.get(normalized.provider)
        coder_output = provider.generate(normalized)
        extracted_claims = self.claim_extractor.extract(coder_output)
        static_findings = self.static_analyzer.analyze(
            coder_output.code,
            normalized.language,
        )
        sandbox_result = self.sandbox_verifier.verify(
            coder_output.code,
            normalized.language,
        )
        policy_decision = self.policy_engine.decide(
            static_findings,
            normalized.risk_level,
            sandbox_result,
        )
        repository = RunRepository(session)
        return repository.create_run(
            normalized_request=normalized,
            coder_output=coder_output,
            extracted_claims=extracted_claims,
            static_findings=static_findings,
            sandbox_result=sandbox_result,
            policy_decision=policy_decision,
        )
