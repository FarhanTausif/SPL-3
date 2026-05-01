from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from dehalu.adapters.language import build_language_registry
from dehalu.adapters.llm import ProviderRegistry
from dehalu.adapters.llm.base import LLMProvider
from dehalu.adapters.llm.runtime import ProviderExecutionError
from dehalu.adapters.tools import ToolGateway
from dehalu.core.settings import Settings
from dehalu.orchestration.execution import build_execution_engine
from dehalu.orchestration.routing import ProviderRouter
from dehalu.schemas import (
    AgentRole,
    ClarificationResult,
    EvidenceKind,
    FusedHallucinationMetrics,
    NormalizedRequest,
    PanelVerdict,
    RepairOutcome,
    RunDetail,
    RunEvent,
    RunLifecycleStatus,
    RunMode,
    RunRequest,
    RunResponse,
    StageStatus,
)
from dehalu.state.models import RunRecord
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
        run_mode=request.run_mode,
        target_runtime=request.target_runtime,
        framework_hint=request.framework_hint,
        acceptance_criteria=request.acceptance_criteria,
        tool_policy=request.tool_policy,
    )


def _infer_language(prompt: str) -> str | None:
    lowered = prompt.lower()
    if "python" in lowered or ".py" in lowered:
        return "python"
    return None


class RequestedProviderUnavailableError(ValueError):
    def __init__(self, provider_name: str, available_providers: set[str]) -> None:
        available = ", ".join(sorted(available_providers)) or "none"
        super().__init__(
            f"Provider '{provider_name}' is unavailable. Configure its API key or choose one of: {available}."
        )
        self.provider_name = provider_name
        self.available_providers = tuple(sorted(available_providers))


class RunOrchestrator:
    def __init__(self, settings: Settings, providers: ProviderRegistry) -> None:
        language_registry = build_language_registry()
        self.settings = settings
        self.providers = providers
        self.claim_extractor = ClaimExtractor(language_registry)
        self.static_analyzer = StaticAnalyzer(language_registry)
        self.sandbox_verifier = SandboxVerifier()
        self.policy_engine = PolicyEngine()
        self.tool_gateway = ToolGateway()
        self.execution_engine = build_execution_engine(
            settings.orchestration_mode,
            self.claim_extractor,
            self.static_analyzer,
            self.sandbox_verifier,
            self.policy_engine,
        )
        self.router = ProviderRouter.from_settings(providers, settings)

    def run(self, request: RunRequest, session: Session) -> RunResponse:
        normalized = normalize_request(request, self.settings)
        if request.provider is None:
            normalized = normalized.model_copy(
                update={"provider": self.settings.resolve_default_provider(self.providers.names())}
            )
        repository = RunRepository(session)
        self._ensure_provider_available(normalized.provider)
        if normalized.run_mode == RunMode.basic:
            provider = self.providers.get(normalized.provider)
            execution_result = self.execution_engine.execute(normalized, provider)
            return repository.complete_run(
                run_id=repository.create_pending_run(normalized_request=normalized, run_mode=RunMode.basic).run_id,
                normalized_request=normalized,
                original_attempt=(
                    execution_result.initial_attempt
                    if execution_result.repair_result.outcome != RepairOutcome.skipped
                    else None
                ),
                final_attempt=execution_result.final_attempt,
                repair_result=execution_result.repair_result,
                orchestration_mode=self.settings.orchestration_mode,
                orchestration_trace=execution_result.orchestration_trace,
                stage_summary=[
                    self._stage("generation", "completed"),
                    self._stage("verification", "completed"),
                    self._stage("policy", "completed"),
                ],
            )

        return repository.create_pending_run(normalized_request=normalized, run_mode=RunMode.advanced)

    def process_claimed_run(self, run_record: RunRecord, session: Session) -> RunResponse | RunDetail:
        repository = RunRepository(session)
        normalized = NormalizedRequest.model_validate(run_record.normalized_request)
        stage_summary: list[StageStatus] = []
        provider_invocations: list[dict] = []

        clarification_provider, clarification, clarification_route = self._run_clarification_chain(normalized)
        provider_invocations.extend(self._collect_provider_invocations_from_clarification(clarification))
        clarification_status = "completed" if not clarification.needs_user_input else "needs_clarification"
        stage_summary.append(
            self._stage(
                "clarification",
                clarification_status,
                {
                    "provider": clarification_provider.name,
                    "ambiguity_flags": clarification.ambiguity_flags,
                    "fallback_used": clarification_route["fallback_used"],
                },
            )
        )
        repository.update_stage_status(
            run_record.id,
            stage="clarification",
            status=clarification_status,
            details=stage_summary[0].details,
            worker_id=self.settings.worker_id,
            lease_seconds=self.settings.worker_lease_seconds,
        )
        repository.append_event(
            run_record.id,
            event_type="stage_completed",
            stage="clarification",
            status=clarification_status,
            message=f"Clarification completed with provider {clarification_provider.name}.",
            payload=stage_summary[0].details,
        )
        repository.set_clarification_result(run_record.id, clarification, stage_summary=stage_summary)
        if clarification.needs_user_input:
            return repository.get_run_detail(run_record.id)

        generation_provider, execution_result, generation_route = self._run_generation_chain(normalized)
        worker_request = normalized.model_copy(update={"provider": generation_provider.name})
        provider_invocations.extend(self._collect_provider_invocations_from_bundle(execution_result.initial_attempt))
        provider_invocations.extend(self._collect_provider_invocations_from_bundle(execution_result.final_attempt))
        if execution_result.repair_result.outcome != RepairOutcome.skipped:
            provider_invocations.extend(self._collect_provider_invocations_from_repair(execution_result.repair_result))
        stage_summary.append(
            self._stage(
                "generation",
                "completed",
                {"provider": generation_provider.name, "fallback_used": generation_route["fallback_used"]},
            )
        )
        repository.update_stage_status(
            run_record.id,
            stage="generation",
            status="completed",
            details=stage_summary[-1].details,
            worker_id=self.settings.worker_id,
            lease_seconds=self.settings.worker_lease_seconds,
        )
        repository.append_event(
            run_record.id,
            event_type="stage_completed",
            stage="generation",
            status="completed",
            message=f"Generation and internal verification completed with provider {generation_provider.name}.",
            payload=stage_summary[-1].details,
        )

        final_attempt = execution_result.final_attempt
        claim_values = [claim.value for claim in final_attempt.extracted_claims]
        tool_records = self.tool_gateway.run_verifier_suite(
            agent_role=AgentRole.judge,
            claims=claim_values,
            request_prompt=clarification.clarified_prompt,
            code=final_attempt.coder_output.code,
            policy=normalized.tool_policy,
        )
        repository.update_stage_status(
            run_record.id,
            stage="tooling",
            status="completed",
            details={"tool_count": len(tool_records)},
            worker_id=self.settings.worker_id,
            lease_seconds=self.settings.worker_lease_seconds,
        )

        judge_available = self.router.get_judge_providers()
        judge_candidates = judge_available or [generation_provider]
        judge_attempts: list[dict] = []
        judge_results = []
        for provider in judge_candidates:
            result = provider.judge(
                worker_request,
                final_attempt.coder_output,
                final_attempt.extracted_claims,
                final_attempt.static_findings,
                final_attempt.sandbox_result,
            )
            invocation = result.metrics.get("provider_invocation")
            judge_attempts.append(self._attempt_payload(provider.name, invocation))
            if self._invocation_success(invocation):
                judge_results.append(result)
            provider_invocations.extend(self._collect_provider_invocations_from_judge(result))
        if not judge_results:
            fallback_provider = judge_candidates[-1]
            fallback_result = fallback_provider.judge(
                worker_request,
                final_attempt.coder_output,
                final_attempt.extracted_claims,
                final_attempt.static_findings,
                final_attempt.sandbox_result,
            )
            judge_results = [fallback_result]
            invocation = fallback_result.metrics.get("provider_invocation")
            judge_attempts.append(self._attempt_payload(fallback_provider.name, invocation))
            provider_invocations.extend(self._collect_provider_invocations_from_judge(fallback_result))

        cove_available = self.router.get_cove_providers()
        cove_candidates = cove_available or [generation_provider]
        cove_attempts: list[dict] = []
        cove_results = []
        for index, provider in enumerate(cove_candidates):
            result = provider.cove(
                worker_request,
                final_attempt.coder_output,
                final_attempt.extracted_claims,
                final_attempt.static_findings,
                final_attempt.sandbox_result,
                judge_results[min(index, len(judge_results) - 1)],
            )
            invocation = result.metrics.get("provider_invocation")
            cove_attempts.append(self._attempt_payload(provider.name, invocation))
            if self._invocation_success(invocation):
                cove_results.append(result)
            provider_invocations.extend(self._collect_provider_invocations_from_cove(result))
        if not cove_results:
            fallback_provider = cove_candidates[-1]
            fallback_result = fallback_provider.cove(
                worker_request,
                final_attempt.coder_output,
                final_attempt.extracted_claims,
                final_attempt.static_findings,
                final_attempt.sandbox_result,
                judge_results[-1],
            )
            cove_results = [fallback_result]
            invocation = fallback_result.metrics.get("provider_invocation")
            cove_attempts.append(self._attempt_payload(fallback_provider.name, invocation))
            provider_invocations.extend(self._collect_provider_invocations_from_cove(fallback_result))

        panel = self._build_panel([result.provider for result in judge_results], judge_results, cove_results)
        repair_selection = self.router.choose_repair_provider(
            judge_results=judge_results,
            generation_provider=generation_provider,
        )
        fused_metrics = self._fuse_metrics(final_attempt, tool_records, panel)

        stage_summary.extend(
            [
                self._stage("tooling", "completed", {"tool_count": len(tool_records)}),
                self._stage(
                    "panel_verification",
                    "completed",
                    {
                        "providers": panel.providers,
                        "consensus_verdict": panel.consensus_verdict,
                        "disagreement_score": panel.disagreement_score,
                    },
                ),
                self._stage(
                    "policy",
                    "completed",
                    {
                        "policy_state": final_attempt.policy_decision.state.value,
                        "repair_provider": repair_selection.provider_name,
                    },
                ),
            ]
        )
        repository.update_stage_status(
            run_record.id,
            stage="panel_verification",
            status="completed",
            details=stage_summary[-2].details,
            worker_id=self.settings.worker_id,
            lease_seconds=self.settings.worker_lease_seconds,
        )
        repository.update_stage_status(
            run_record.id,
            stage="policy",
            status="completed",
            details=stage_summary[-1].details,
            worker_id=self.settings.worker_id,
            lease_seconds=self.settings.worker_lease_seconds,
        )

        return repository.complete_run(
            run_id=run_record.id,
            normalized_request=worker_request,
            original_attempt=(
                execution_result.initial_attempt
                if execution_result.repair_result.outcome != RepairOutcome.skipped
                else None
            ),
            final_attempt=final_attempt,
            repair_result=execution_result.repair_result,
            orchestration_mode=self.settings.orchestration_mode,
            orchestration_trace=execution_result.orchestration_trace,
            clarification_result=clarification,
            fused_metrics=fused_metrics,
            stage_summary=stage_summary,
            extra_evidence=[
                (
                    EvidenceKind.tool,
                    {
                        "invocations": [record.model_dump(mode="json") for record in tool_records],
                        "count": len(tool_records),
                    },
                ),
                (EvidenceKind.panel, panel.model_dump(mode="json")),
                (EvidenceKind.fusion, fused_metrics.model_dump(mode="json")),
                (
                    EvidenceKind.provider_invocation,
                    {
                        "invocations": provider_invocations,
                        "count": len(provider_invocations),
                    },
                ),
                (
                    EvidenceKind.routing,
                    {
                        "clarification_provider": clarification_provider.name,
                        "clarification_fallback_used": clarification_route["fallback_used"],
                        "generation_provider": generation_provider.name,
                        "generation_fallback_used": generation_route["fallback_used"],
                        "judge_panel": panel.providers,
                        "cove_providers": [result.provider for result in cove_results],
                        "repair_provider": repair_selection.provider_name,
                        "repair_reason": repair_selection.reason,
                        "repair_fallback_used": repair_selection.fallback_used,
                        "repair_selected_via": repair_selection.selected_via,
                        "repair_candidate_chain": list(repair_selection.candidate_chain),
                        "role_routes": {
                            "clarification": clarification_route,
                            "generation": generation_route,
                            "judge": {
                                "configured": list(self.router.matrix.judges),
                                "available": [provider.name for provider in judge_available],
                                "selected": [result.provider for result in judge_results],
                                "fallback_used": any(not self._invocation_success(item.get("invocation")) for item in judge_attempts)
                                or not bool(judge_available),
                                "attempts": judge_attempts,
                            },
                            "cove": {
                                "configured": list(self.router.matrix.cove),
                                "available": [provider.name for provider in cove_available],
                                "selected": [result.provider for result in cove_results],
                                "fallback_used": any(not self._invocation_success(item.get("invocation")) for item in cove_attempts)
                                or not bool(cove_available),
                                "attempts": cove_attempts,
                            },
                            "repair": {
                                "configured": list(self.router.matrix.repair),
                                "selected": repair_selection.provider_name,
                                "fallback_used": repair_selection.fallback_used,
                                "selected_via": repair_selection.selected_via,
                                "candidate_chain": list(repair_selection.candidate_chain),
                            },
                        },
                        "routing_policy_version": self.settings.routing_policy_version,
                        "prompt_policy_version": self.settings.prompt_policy_version,
                    },
                ),
                (EvidenceKind.clarification, clarification.model_dump(mode="json")),
            ],
        )

    def get_run_detail(self, run_id: str, session: Session) -> RunDetail:
        return RunRepository(session).get_run_detail(run_id)

    def get_run_events(self, run_id: str, session: Session) -> list[RunEvent]:
        return RunRepository(session).get_run_events(run_id)

    def _build_panel(self, providers: list[str], judge_results, cove_results) -> PanelVerdict:
        verdicts = [result.verdict.value for result in judge_results] + [result.verdict.value for result in cove_results]
        disagreement = 0.0 if len(set(verdicts)) <= 1 else min(1.0, len(set(verdicts)) / max(1, len(verdicts)))
        consensus = "pass"
        if any(result.verdict.value == "fail" for result in judge_results + cove_results):
            consensus = "fail"
        elif any(result.verdict.value == "uncertain" for result in judge_results + cove_results):
            consensus = "uncertain"
        return PanelVerdict(
            stage="panel_verification",
            providers=providers,
            judge_results=judge_results,
            cove_results=cove_results,
            disagreement_score=disagreement,
            consensus_verdict=consensus,
            metadata={
                "judge_count": len(judge_results),
                "cove_count": len(cove_results),
                "judge_verdicts": [result.verdict.value for result in judge_results],
                "cove_verdicts": [result.verdict.value for result in cove_results],
            },
        )

    def _fuse_metrics(self, final_attempt, tool_records, panel: PanelVerdict) -> FusedHallucinationMetrics:
        unsupported_claims = final_attempt.cove_result.metrics.get("unsupported_claim_count", 0)
        claim_count = max(1, len(final_attempt.extracted_claims))
        unsupported_ratio = min(1.0, unsupported_claims / claim_count)
        tool_supported = 0
        for record in tool_records:
            if record.tool_name == "claim_to_evidence_linker":
                linked = record.metadata.get("linked_claims", {})
                supported = sum(1 for verdict in linked.values() if verdict == "supported")
                tool_supported = supported / max(1, len(linked))
                break
        execution_validity = 1.0 if final_attempt.sandbox_result.status.value == "passed" else 0.0
        dependency_score = 0.2 if any(
            record.tool_name == "package_registry_lookup" and record.metadata.get("unknown")
            for record in tool_records
        ) else 0.9
        api_score = 0.3 if any(
            record.tool_name == "python_symbol_validation" and record.metadata.get("missing")
            for record in tool_records
        ) else 0.9
        alignment_score = 0.9 if final_attempt.policy_decision.state.value == "accept" else 0.4
        overall = min(
            1.0,
            (
                final_attempt.judge_result.hallucination_score
                + final_attempt.cove_result.hallucination_score
                + panel.disagreement_score
                + unsupported_ratio
            )
            / 4,
        )
        return FusedHallucinationMetrics(
            requirement_alignment_score=alignment_score,
            dependency_plausibility_score=dependency_score,
            api_symbol_validity_score=api_score,
            unsupported_assumption_score=unsupported_ratio,
            execution_validity_score=execution_validity,
            judge_disagreement_score=panel.disagreement_score,
            tool_supported_claim_ratio=tool_supported,
            overall_hallucination_score=overall,
            metadata={
                "policy_state": final_attempt.policy_decision.state.value,
                "decision_driver": (
                    "deterministic"
                    if final_attempt.sandbox_result.status.value != "passed" or final_attempt.static_findings
                    else "panel"
                ),
            },
        )

    def _stage(self, name: str, status: str, details: dict | None = None) -> StageStatus:
        now = datetime.now(timezone.utc)
        return StageStatus(stage=name, status=status, started_at=now, finished_at=now, details=details or {})

    def _ensure_provider_available(self, provider_name: str) -> None:
        available = set(self.providers.names())
        if provider_name in available:
            return
        if provider_name in (self.settings.KNOWN_PROVIDERS - {"auto"}):
            raise RequestedProviderUnavailableError(provider_name, available)
        self.providers.get(provider_name)

    def _run_clarification_chain(self, normalized: NormalizedRequest) -> tuple[LLMProvider, ClarificationResult, dict[str, object]]:
        candidates = self.router.get_clarification_candidates()
        configured = list(self.router.matrix.clarification)
        if not candidates:
            requested = (
                normalized.provider
                if normalized.provider in self.providers.names()
                else self.settings.resolve_default_provider(self.providers.names())
            )
            candidates = [self.providers.get(requested)]
            configured = [requested]
        attempts: list[dict] = []
        fallback_used = False
        for index, provider in enumerate(candidates):
            clarification = provider.clarify(normalized)
            invocation = clarification.metadata.get("provider_invocation", {})
            attempts.append(self._attempt_payload(provider.name, invocation))
            if invocation.get("success", True) or index == len(candidates) - 1:
                return provider, clarification, {
                    "configured": configured,
                    "available": [candidate.name for candidate in candidates],
                    "selected": provider.name,
                    "fallback_used": fallback_used,
                    "attempts": attempts,
                }
            fallback_used = True
        provider = candidates[-1]
        clarification = provider.clarify(normalized)
        attempts.append(self._attempt_payload(provider.name, clarification.metadata.get("provider_invocation")))
        return provider, clarification, {
            "configured": configured,
            "available": [candidate.name for candidate in candidates],
            "selected": provider.name,
            "fallback_used": True,
            "attempts": attempts,
        }

    def _run_generation_chain(self, normalized: NormalizedRequest):
        candidates = self.router.get_generation_candidates(normalized.provider)
        configured = list(self.router.matrix.generation)
        if not candidates:
            candidates = [self.providers.get(normalized.provider)]
            configured = [normalized.provider]
        fallback_used = False
        attempts: list[dict] = []
        last_error: Exception | None = None
        for index, provider in enumerate(candidates):
            try:
                worker_request = normalized.model_copy(update={"provider": provider.name})
                execution = self.execution_engine.execute(worker_request, provider)
                attempts.append(self._attempt_payload(provider.name, {"success": True}))
                return provider, execution, {
                    "configured": configured,
                    "available": [candidate.name for candidate in candidates],
                    "selected": provider.name,
                    "fallback_used": fallback_used,
                    "attempts": attempts,
                }
            except ProviderExecutionError as exc:
                last_error = exc
                attempts.append(self._attempt_payload(provider.name, exc.record.model_dump(mode="json")))
                if index < len(candidates) - 1:
                    fallback_used = True
                    continue
                raise
            except Exception as exc:
                last_error = exc
                attempts.append(
                    self._attempt_payload(
                        provider.name,
                        {"success": False, "failure_kind": "internal_error", "message": str(exc)},
                    )
                )
                raise
        raise last_error or RuntimeError("No generation provider could execute the run.")

    def _attempt_payload(self, provider_name: str, invocation: dict | None) -> dict:
        payload: dict = {"provider": provider_name}
        if isinstance(invocation, dict):
            payload["invocation"] = invocation
            payload["success"] = invocation.get("success", True)
            payload["failure_kind"] = invocation.get("failure_kind", "none")
        else:
            payload["invocation"] = None
            payload["success"] = True
            payload["failure_kind"] = "none"
        return payload

    def _invocation_success(self, invocation: dict | None) -> bool:
        if isinstance(invocation, dict):
            return bool(invocation.get("success", True))
        return True

    def _collect_provider_invocations_from_clarification(self, clarification: ClarificationResult) -> list[dict]:
        invocation = clarification.metadata.get("provider_invocation")
        return [invocation] if invocation else []

    def _collect_provider_invocations_from_bundle(self, attempt) -> list[dict]:
        invocations: list[dict] = []
        for source in (
            attempt.coder_output.metadata.get("provider_invocation"),
            attempt.judge_result.metrics.get("provider_invocation"),
            attempt.cove_result.metrics.get("provider_invocation"),
        ):
            if source:
                invocations.append(source)
        return invocations

    def _collect_provider_invocations_from_repair(self, repair_result) -> list[dict]:
        invocations: list[dict] = []
        for attempt in repair_result.attempts:
            invocation = attempt.metadata.get("provider_invocation")
            if invocation:
                invocations.append(invocation)
        return invocations

    def _collect_provider_invocations_from_judge(self, judge_result) -> list[dict]:
        invocation = judge_result.metrics.get("provider_invocation")
        return [invocation] if invocation else []

    def _collect_provider_invocations_from_cove(self, cove_result) -> list[dict]:
        invocation = cove_result.metrics.get("provider_invocation")
        return [invocation] if invocation else []
