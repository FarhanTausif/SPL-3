from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from dehalu.adapters.language import build_language_registry
from dehalu.adapters.llm import ProviderRegistry
from dehalu.adapters.tools import ToolGateway
from dehalu.core.settings import Settings
from dehalu.orchestration.execution import build_execution_engine
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

    def run(self, request: RunRequest, session: Session) -> RunResponse:
        normalized = normalize_request(request, self.settings)
        repository = RunRepository(session)
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

        created = repository.create_pending_run(normalized_request=normalized, run_mode=RunMode.advanced)
        self.process_advanced_run(created.run_id, normalized, repository)
        return RunRepository(session).get_run_response(created.run_id)

    def process_advanced_run(
        self,
        run_id: str,
        normalized: NormalizedRequest,
        repository: RunRepository,
    ) -> None:
        repository.mark_running(run_id)
        stage_summary = [self._stage("clarification", "running")]
        primary_provider = self.providers.get(normalized.provider)
        clarification = primary_provider.clarify(normalized)
        stage_summary[0] = self._stage(
            "clarification",
            "completed" if not clarification.needs_user_input else "needs_clarification",
            {"ambiguity_flags": clarification.ambiguity_flags},
        )
        repository.set_clarification_result(run_id, clarification, stage_summary=stage_summary)
        if clarification.needs_user_input:
            return

        stage_summary.append(self._stage("generation", "running"))
        execution_result = self.execution_engine.execute(normalized, primary_provider)
        stage_summary[-1] = self._stage("generation", "completed")

        final_attempt = execution_result.final_attempt
        claim_values = [claim.value for claim in final_attempt.extracted_claims]
        tool_records = self.tool_gateway.run_verifier_suite(
            agent_role=AgentRole.judge,
            claims=claim_values,
            request_prompt=clarification.clarified_prompt,
            code=final_attempt.coder_output.code,
            policy=normalized.tool_policy,
        )

        judge_provider_names = [name for name in self.providers.names() if name != "fake"]
        judge_providers = [self.providers.get(name) for name in judge_provider_names] or [primary_provider]
        judge_results = [
            provider.judge(
                normalized,
                final_attempt.coder_output,
                final_attempt.extracted_claims,
                final_attempt.static_findings,
                final_attempt.sandbox_result,
            )
            for provider in judge_providers
        ]
        cove_results = [
            provider.cove(
                normalized,
                final_attempt.coder_output,
                final_attempt.extracted_claims,
                final_attempt.static_findings,
                final_attempt.sandbox_result,
                judge_results[index],
            )
            for index, provider in enumerate(judge_providers)
        ]
        panel = self._build_panel(judge_provider_names or [primary_provider.name], judge_results, cove_results)
        fused_metrics = self._fuse_metrics(final_attempt, tool_records, panel)

        stage_summary.extend(
            [
                self._stage("tooling", "completed", {"tool_count": len(tool_records)}),
                self._stage("panel_verification", "completed", {"providers": panel.providers}),
                self._stage("policy", "completed", {"policy_state": final_attempt.policy_decision.state.value}),
            ]
        )

        repository.complete_run(
            run_id=run_id,
            normalized_request=normalized,
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
                    EvidenceKind.routing,
                    {
                        "primary_provider": primary_provider.name,
                        "judge_panel": panel.providers,
                        "repair_provider": primary_provider.name,
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
            metadata={"judge_count": len(judge_results), "cove_count": len(cove_results)},
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
            metadata={"policy_state": final_attempt.policy_decision.state.value},
        )

    def _stage(self, name: str, status: str, details: dict | None = None) -> StageStatus:
        now = datetime.now(timezone.utc)
        return StageStatus(stage=name, status=status, started_at=now, finished_at=now, details=details or {})
