from __future__ import annotations

from time import perf_counter

from sqlalchemy.orm import Session

from dehalu.adapters.language import build_language_registry
from dehalu.adapters.llm import LLMProvider, ProviderRegistry
from dehalu.core.settings import Settings
from dehalu.schemas import (
    CoderOutput,
    NormalizedRequest,
    RepairAttempt,
    RepairOutcome,
    RepairResult,
    RepairTrigger,
    RunRequest,
    RunResponse,
)
from dehalu.state.repository import EvaluationBundle, RunRepository
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
        initial_output = provider.generate(normalized)
        initial_attempt = self._evaluate_attempt(
            normalized,
            provider,
            initial_output,
            attempt_number=1,
            attempt_stage="original",
            allow_repair=True,
        )
        repair_result = RepairResult(
            outcome=RepairOutcome.skipped,
            attempts=[],
            final_attempt_number=1,
            metrics={
                "attempted": False,
                "initial_policy_state": initial_attempt.policy_decision.state.value,
                "final_policy_state": initial_attempt.policy_decision.state.value,
            },
        )
        final_attempt = initial_attempt

        if initial_attempt.policy_decision.state.value == "repair_and_retry":
            repair_trigger = RepairTrigger(
                initial_attempt.policy_decision.metrics["repair_trigger"]
            )
            repair_started_at = perf_counter()
            repaired_output = provider.repair(
                normalized,
                initial_attempt.coder_output,
                initial_attempt.policy_decision,
                initial_attempt.judge_result,
                initial_attempt.cove_result,
            )
            repair_attempt = RepairAttempt(
                attempt_number=2,
                trigger=repair_trigger,
                provider=repaired_output.provider,
                model=repaired_output.model,
                duration_ms=round((perf_counter() - repair_started_at) * 1000, 3),
                input_code=initial_attempt.coder_output.code,
                output_code=repaired_output.code,
                summary=_summarize_repair(initial_attempt.coder_output, repaired_output),
                metadata={"execution_notes": repaired_output.execution_notes},
            )
            final_attempt = self._evaluate_attempt(
                normalized,
                provider,
                repaired_output,
                attempt_number=2,
                attempt_stage="repair",
                allow_repair=False,
            )
            repair_result = RepairResult(
                outcome=(
                    RepairOutcome.succeeded
                    if final_attempt.policy_decision.state.value == "accept"
                    else RepairOutcome.failed
                ),
                attempts=[repair_attempt],
                final_attempt_number=2,
                metrics={
                    "attempted": True,
                    "initial_policy_state": initial_attempt.policy_decision.state.value,
                    "final_policy_state": final_attempt.policy_decision.state.value,
                    "trigger": repair_trigger.value,
                },
            )

        repository = RunRepository(session)
        return repository.create_run(
            normalized_request=normalized,
            original_attempt=initial_attempt if repair_result.outcome != RepairOutcome.skipped else None,
            final_attempt=final_attempt,
            repair_result=repair_result,
        )

    def _evaluate_attempt(
        self,
        normalized: NormalizedRequest,
        provider: LLMProvider,
        coder_output: CoderOutput,
        *,
        attempt_number: int,
        attempt_stage: str,
        allow_repair: bool,
    ) -> EvaluationBundle:
        extracted_claims = self.claim_extractor.extract(coder_output)
        static_findings = self.static_analyzer.analyze(
            coder_output.code,
            normalized.language,
        )
        sandbox_result = self.sandbox_verifier.verify(
            coder_output.code,
            normalized.language,
        )
        judge_result = provider.judge(
            normalized,
            coder_output,
            extracted_claims,
            static_findings,
            sandbox_result,
        )
        cove_result = provider.cove(
            normalized,
            coder_output,
            extracted_claims,
            static_findings,
            sandbox_result,
            judge_result,
        )
        policy_decision = self.policy_engine.decide(
            static_findings,
            normalized.risk_level,
            sandbox_result,
            judge_result,
            cove_result,
            allow_repair=allow_repair,
        )
        return EvaluationBundle(
            attempt_number=attempt_number,
            attempt_stage=attempt_stage,
            coder_output=coder_output,
            extracted_claims=extracted_claims,
            static_findings=static_findings,
            sandbox_result=sandbox_result,
            judge_result=judge_result,
            cove_result=cove_result,
            policy_decision=policy_decision,
        )


def _summarize_repair(original_output: CoderOutput, repaired_output: CoderOutput) -> str:
    if not repaired_output.code.strip():
        return "Repair attempt did not return code."
    if repaired_output.code.strip() == original_output.code.strip():
        return "Repair attempt returned code unchanged."
    return "Repair attempt returned revised code for re-verification."
