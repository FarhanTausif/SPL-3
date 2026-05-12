from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from dehalu.schemas import (
    ClarificationResult,
    CoderOutput,
    CoVeResult,
    EvidenceKind,
    ExtractedClaim,
    FusedHallucinationMetrics,
    JudgeResult,
    NormalizedRequest,
    OrchestrationTraceEntry,
    PolicyDecision,
    RepairAttempt,
    RepairOutcome,
    RepairResult,
    RunDetail,
    RunEvent,
    RunLifecycleStatus,
    RunMode,
    RunResponse,
    SandboxResult,
    StageStatus,
    StaticFinding,
    VerificationEvidence,
)
from dehalu.state.models import EventRecord, EvidenceRecord, RunRecord


class RunNotFoundError(ValueError):
    pass


@dataclass(slots=True)
class EvaluationBundle:
    attempt_number: int
    attempt_stage: str
    coder_output: CoderOutput
    extracted_claims: list[ExtractedClaim]
    static_findings: list[StaticFinding]
    sandbox_result: SandboxResult
    judge_result: JudgeResult
    cove_result: CoVeResult
    policy_decision: PolicyDecision


class RunRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_pending_run(
        self,
        *,
        normalized_request: NormalizedRequest,
        run_mode: RunMode,
    ) -> RunResponse:
        run_id = str(uuid4())
        run_record = RunRecord(
            id=run_id,
            prompt=normalized_request.prompt,
            language=normalized_request.language,
            risk_level=normalized_request.risk_level.value,
            provider=normalized_request.provider,
            status=RunLifecycleStatus.queued.value,
            run_mode=run_mode.value,
            queued_at=datetime.now(timezone.utc),
            started_at=None,
            completed_at=None,
            claimed_by=None,
            last_heartbeat_at=None,
            lease_expires_at=None,
            attempt_count=0,
            last_error=None,
            normalized_request=normalized_request.model_dump(mode="json"),
            coder_output=None,
            policy_decision=None,
            clarification_result=None,
            fused_metrics=None,
            stage_summary=[],
            evidence=[],
            events=[],
        )
        self.session.add(run_record)
        self.session.commit()
        self.append_event(
            run_id,
            event_type="run_created",
            stage="lifecycle",
            status=RunLifecycleStatus.queued.value,
            message="Run was created and queued for execution.",
            payload={"run_mode": run_mode.value},
        )
        return RunResponse(
            run_id=run_id,
            normalized_request=normalized_request,
            status=RunLifecycleStatus.queued,
            stage_summary=[],
            evidence_ids=[],
        )

    def claim_next_advanced_run(
        self,
        *,
        worker_id: str,
        lease_seconds: int,
    ) -> RunRecord | None:
        now = datetime.now(timezone.utc)
        statement = (
            select(RunRecord)
            .where(
                RunRecord.run_mode == RunMode.advanced.value,
                or_(
                    RunRecord.status == RunLifecycleStatus.queued.value,
                    (
                        RunRecord.status == RunLifecycleStatus.running.value
                    )
                    & (
                        or_(
                            RunRecord.lease_expires_at.is_(None),
                            RunRecord.lease_expires_at < now,
                        )
                    ),
                ),
            )
            .order_by(RunRecord.queued_at.asc(), RunRecord.created_at.asc())
            .options(selectinload(RunRecord.evidence), selectinload(RunRecord.events))
        )
        run_record = self.session.execute(statement).scalars().first()
        if run_record is None:
            return None
        lease_expires_at = now + timedelta(seconds=lease_seconds)
        run_record.status = RunLifecycleStatus.running.value
        run_record.claimed_by = worker_id
        run_record.started_at = run_record.started_at or now
        run_record.last_heartbeat_at = now
        run_record.lease_expires_at = lease_expires_at
        run_record.attempt_count = (run_record.attempt_count or 0) + 1
        self.session.commit()
        self.append_event(
            run_record.id,
            event_type="run_claimed",
            stage="lifecycle",
            status=RunLifecycleStatus.running.value,
            message="Run was claimed by worker.",
            payload={
                "worker_id": worker_id,
                "lease_expires_at": lease_expires_at.isoformat(),
                "attempt_count": run_record.attempt_count,
            },
        )
        return self._get_run(run_record.id)

    def mark_running(self, run_id: str, *, worker_id: str | None = None, lease_seconds: int | None = None) -> None:
        run_record = self._get_run(run_id)
        now = datetime.now(timezone.utc)
        run_record.status = RunLifecycleStatus.running.value
        run_record.started_at = run_record.started_at or now
        if worker_id is not None:
            run_record.claimed_by = worker_id
            run_record.last_heartbeat_at = now
        if lease_seconds is not None:
            run_record.lease_expires_at = now + timedelta(seconds=lease_seconds)
        self.session.commit()
        self.append_event(
            run_id,
            event_type="run_started",
            stage="lifecycle",
            status=RunLifecycleStatus.running.value,
            message="Run execution started.",
        )

    def heartbeat_run(self, run_id: str, *, worker_id: str, lease_seconds: int) -> None:
        run_record = self._get_run(run_id)
        now = datetime.now(timezone.utc)
        if run_record.claimed_by != worker_id:
            raise ValueError(f"Run {run_id} is not claimed by worker {worker_id}.")
        run_record.last_heartbeat_at = now
        run_record.lease_expires_at = now + timedelta(seconds=lease_seconds)
        self.session.commit()

    def update_stage_status(
        self,
        run_id: str,
        *,
        stage: str,
        status: str,
        details: dict | None = None,
        worker_id: str | None = None,
        lease_seconds: int | None = None,
    ) -> None:
        run_record = self._get_run(run_id)
        now = datetime.now(timezone.utc)
        current = [StageStatus.model_validate(item) for item in (run_record.stage_summary or [])]
        replaced = False
        for index, entry in enumerate(current):
            if entry.stage == stage:
                current[index] = StageStatus(
                    stage=stage,
                    status=status,
                    started_at=entry.started_at or now,
                    finished_at=now if status not in {"queued", "running"} else None,
                    details={**entry.details, **(details or {})},
                )
                replaced = True
                break
        if not replaced:
            current.append(
                StageStatus(
                    stage=stage,
                    status=status,
                    started_at=now,
                    finished_at=now if status not in {"queued", "running"} else None,
                    details=details or {},
                )
            )
        run_record.stage_summary = [stage_status.model_dump(mode="json") for stage_status in current]
        if worker_id is not None and lease_seconds is not None:
            if run_record.claimed_by != worker_id:
                raise ValueError(f"Run {run_id} is not claimed by worker {worker_id}.")
            run_record.last_heartbeat_at = now
            run_record.lease_expires_at = now + timedelta(seconds=lease_seconds)
        self.session.commit()

    def release_run_claim(self, run_id: str) -> None:
        run_record = self._get_run(run_id)
        run_record.claimed_by = None
        run_record.last_heartbeat_at = None
        run_record.lease_expires_at = None
        self.session.commit()

    def set_clarification_result(
        self,
        run_id: str,
        clarification_result: ClarificationResult,
        *,
        stage_summary: list[StageStatus],
    ) -> None:
        run_record = self._get_run(run_id)
        run_record.clarification_result = clarification_result.model_dump(mode="json")
        run_record.stage_summary = [stage.model_dump(mode="json") for stage in stage_summary]
        run_record.status = (
            RunLifecycleStatus.needs_clarification.value
            if clarification_result.needs_user_input
            else RunLifecycleStatus.running.value
        )
        if clarification_result.needs_user_input:
            run_record.completed_at = datetime.now(timezone.utc)
            run_record.claimed_by = None
            run_record.last_heartbeat_at = None
            run_record.lease_expires_at = None
        self.session.commit()
        self.append_event(
            run_id,
            event_type="clarification_completed",
            stage="clarification",
            status=run_record.status,
            message="Clarification stage completed.",
            payload=clarification_result.model_dump(mode="json"),
        )

    def complete_run(
        self,
        *,
        run_id: str,
        normalized_request: NormalizedRequest,
        final_attempt: EvaluationBundle,
        repair_result: RepairResult,
        original_attempt: EvaluationBundle | None = None,
        orchestration_mode: str = "direct",
        orchestration_trace: list[OrchestrationTraceEntry] | None = None,
        clarification_result: ClarificationResult | None = None,
        fused_metrics: FusedHallucinationMetrics | None = None,
        stage_summary: list[StageStatus] | None = None,
        extra_evidence: list[tuple[EvidenceKind, dict]] | None = None,
        final_status: RunLifecycleStatus = RunLifecycleStatus.completed,
    ) -> RunResponse:
        run_record = self._get_run(run_id)
        evidence_records: list[EvidenceRecord] = []
        if original_attempt is not None:
            evidence_records.extend(
                self._build_attempt_evidence(
                    run_id,
                    original_attempt,
                    orchestration_mode=orchestration_mode,
                )
            )

        if repair_result.outcome != RepairOutcome.skipped:
            for repair_attempt in repair_result.attempts:
                evidence_records.append(
                    EvidenceRecord(
                        id=str(uuid4()),
                        run_id=run_id,
                        kind=EvidenceKind.repair.value,
                        payload=repair_attempt.model_dump(mode="json"),
                    )
                )

        evidence_records.extend(
            self._build_attempt_evidence(
                run_id,
                final_attempt,
                orchestration_mode=orchestration_mode,
            )
        )
        if orchestration_trace:
            evidence_records.append(
                EvidenceRecord(
                    id=str(uuid4()),
                    run_id=run_id,
                    kind=EvidenceKind.orchestration.value,
                    payload={
                        "orchestration_mode": orchestration_mode,
                        "entry_count": len(orchestration_trace),
                        "entries": [entry.model_dump(mode="json") for entry in orchestration_trace],
                    },
                )
            )
        for kind, payload in extra_evidence or []:
            evidence_records.append(
                EvidenceRecord(
                    id=str(uuid4()),
                    run_id=run_id,
                    kind=kind.value,
                    payload=payload,
                )
            )

        run_record.status = final_status.value
        run_record.completed_at = datetime.now(timezone.utc)
        run_record.claimed_by = None
        run_record.last_heartbeat_at = None
        run_record.lease_expires_at = None
        run_record.last_error = None
        run_record.coder_output = final_attempt.coder_output.model_dump(mode="json")
        run_record.policy_decision = final_attempt.policy_decision.model_dump(mode="json")
        run_record.clarification_result = (
            clarification_result.model_dump(mode="json") if clarification_result else run_record.clarification_result
        )
        run_record.fused_metrics = fused_metrics.model_dump(mode="json") if fused_metrics else None
        run_record.stage_summary = [stage.model_dump(mode="json") for stage in (stage_summary or [])]
        run_record.evidence.extend(evidence_records)
        self.session.commit()

        self.append_event(
            run_id,
            event_type="run_completed",
            stage="lifecycle",
            status=final_status.value,
            message="Run execution completed.",
            payload={"policy_state": final_attempt.policy_decision.state.value},
        )

        return RunResponse(
            run_id=run_id,
            normalized_request=normalized_request,
            status=final_status,
            stage_summary=stage_summary or [],
            clarification_result=clarification_result,
            fused_metrics=fused_metrics,
            coder_output=final_attempt.coder_output,
            extracted_claims=final_attempt.extracted_claims,
            static_findings=final_attempt.static_findings,
            sandbox_result=final_attempt.sandbox_result,
            judge_result=final_attempt.judge_result,
            cove_result=final_attempt.cove_result,
            repair_result=repair_result,
            policy_decision=final_attempt.policy_decision,
            evidence_ids=[record.id for record in evidence_records],
        )

    def fail_run(self, run_id: str, message: str, *, stage_summary: list[StageStatus] | None = None) -> RunDetail:
        run_record = self._get_run(run_id)
        run_record.status = RunLifecycleStatus.failed.value
        run_record.completed_at = datetime.now(timezone.utc)
        run_record.claimed_by = None
        run_record.last_heartbeat_at = None
        run_record.lease_expires_at = None
        run_record.last_error = message
        run_record.stage_summary = [stage.model_dump(mode="json") for stage in (stage_summary or [])]
        self.session.commit()
        self.append_event(
            run_id,
            event_type="run_failed",
            stage="lifecycle",
            status=RunLifecycleStatus.failed.value,
            message=message,
        )
        return self.get_run_detail(run_id)

    def append_event(
        self,
        run_id: str,
        *,
        event_type: str,
        stage: str,
        status: str,
        message: str,
        payload: dict | None = None,
    ) -> None:
        run_record = self._get_run(run_id)
        next_sequence = len(run_record.events) + 1
        event_record = EventRecord(
            id=str(uuid4()),
            run_id=run_id,
            sequence=next_sequence,
            event_type=event_type,
            stage=stage,
            status=status,
            message=message,
            payload=payload or {},
        )
        self.session.add(event_record)
        self.session.commit()

    def _build_attempt_evidence(
        self,
        run_id: str,
        attempt: EvaluationBundle,
        *,
        orchestration_mode: str,
    ) -> list[EvidenceRecord]:
        attempt_metadata = {
            "attempt_number": attempt.attempt_number,
            "attempt_stage": attempt.attempt_stage,
            "orchestration_mode": orchestration_mode,
        }
        return [
            EvidenceRecord(
                id=str(uuid4()),
                run_id=run_id,
                kind=EvidenceKind.claim_extraction.value,
                payload={
                    **attempt_metadata,
                    "stage": "extract_claims",
                    "task_name": f"{attempt.attempt_stage}_extract_claims",
                    "claims": [claim.model_dump(mode="json") for claim in attempt.extracted_claims],
                    "claim_count": len(attempt.extracted_claims),
                },
            ),
            EvidenceRecord(
                id=str(uuid4()),
                run_id=run_id,
                kind=EvidenceKind.static_analysis.value,
                payload={
                    **attempt_metadata,
                    "stage": "static_analysis",
                    "task_name": f"{attempt.attempt_stage}_static_analysis",
                    "findings": [finding.model_dump(mode="json") for finding in attempt.static_findings],
                    "finding_count": len(attempt.static_findings),
                },
            ),
            EvidenceRecord(
                id=str(uuid4()),
                run_id=run_id,
                kind=EvidenceKind.sandbox.value,
                payload={
                    **attempt_metadata,
                    "stage": "sandbox_verify",
                    "task_name": f"{attempt.attempt_stage}_sandbox_verify",
                    **attempt.sandbox_result.model_dump(mode="json"),
                },
            ),
            EvidenceRecord(
                id=str(uuid4()),
                run_id=run_id,
                kind=EvidenceKind.judge.value,
                payload={
                    **attempt_metadata,
                    "stage": "judge",
                    "task_name": f"{attempt.attempt_stage}_judge_output",
                    **attempt.judge_result.model_dump(mode="json"),
                },
            ),
            EvidenceRecord(
                id=str(uuid4()),
                run_id=run_id,
                kind=EvidenceKind.cove.value,
                payload={
                    **attempt_metadata,
                    "stage": "cove",
                    "task_name": f"{attempt.attempt_stage}_cove_output",
                    **attempt.cove_result.model_dump(mode="json"),
                },
            ),
            EvidenceRecord(
                id=str(uuid4()),
                run_id=run_id,
                kind=EvidenceKind.policy.value,
                payload={
                    **attempt_metadata,
                    "stage": "policy_decide",
                    "task_name": f"{attempt.attempt_stage}_policy_decide",
                    **attempt.policy_decision.model_dump(mode="json"),
                },
            ),
        ]

    def get_run_detail(self, run_id: str) -> RunDetail:
        run_record = self._get_run(run_id)
        evidence_summary = Counter(record.kind for record in run_record.evidence)
        policy_decision = (
            PolicyDecision.model_validate(run_record.policy_decision)
            if run_record.policy_decision is not None
            else None
        )
        return RunDetail(
            run_id=run_record.id,
            created_at=run_record.created_at,
            normalized_request=NormalizedRequest.model_validate(run_record.normalized_request),
            status=RunLifecycleStatus(run_record.status),
            policy_decision=policy_decision,
            clarification_result=(
                ClarificationResult.model_validate(run_record.clarification_result)
                if run_record.clarification_result is not None
                else None
            ),
            fused_metrics=(
                FusedHallucinationMetrics.model_validate(run_record.fused_metrics)
                if run_record.fused_metrics is not None
                else None
            ),
            coder_output=(
                CoderOutput.model_validate(run_record.coder_output)
                if run_record.coder_output is not None
                else None
            ),
            repair_result=self._reconstruct_repair_result(run_record, policy_decision),
            stage_summary=[
                StageStatus.model_validate(item)
                for item in (run_record.stage_summary or [])
            ],
            evidence_summary=dict(evidence_summary),
        )

    def get_run_response(self, run_id: str) -> RunResponse:
        run_record = self._get_run(run_id)
        return RunResponse(
            run_id=run_record.id,
            normalized_request=NormalizedRequest.model_validate(run_record.normalized_request),
            status=RunLifecycleStatus(run_record.status),
            stage_summary=[
                StageStatus.model_validate(item)
                for item in (run_record.stage_summary or [])
            ],
            clarification_result=(
                ClarificationResult.model_validate(run_record.clarification_result)
                if run_record.clarification_result is not None
                else None
            ),
            fused_metrics=(
                FusedHallucinationMetrics.model_validate(run_record.fused_metrics)
                if run_record.fused_metrics is not None
                else None
            ),
            coder_output=(
                CoderOutput.model_validate(run_record.coder_output)
                if run_record.coder_output is not None
                else None
            ),
            policy_decision=(
                PolicyDecision.model_validate(run_record.policy_decision)
                if run_record.policy_decision is not None
                else None
            ),
            evidence_ids=[record.id for record in run_record.evidence],
        )

    def get_run_evidence(self, run_id: str) -> list[VerificationEvidence]:
        run_record = self._get_run(run_id)
        return [
            VerificationEvidence(
                id=record.id,
                run_id=record.run_id,
                kind=record.kind,
                payload=record.payload,
                created_at=record.created_at,
            )
            for record in run_record.evidence
        ]

    def get_run_events(self, run_id: str) -> list[RunEvent]:
        run_record = self._get_run(run_id)
        return [
            RunEvent(
                sequence=event.sequence,
                event_type=event.event_type,
                stage=event.stage,
                status=event.status,
                message=event.message,
                created_at=event.created_at,
                payload=event.payload,
            )
            for event in run_record.events
        ]

    def _reconstruct_repair_result(
        self,
        run_record: RunRecord,
        policy_decision: PolicyDecision | None,
    ) -> RepairResult | None:
        attempts = [
            RepairAttempt.model_validate(record.payload)
            for record in run_record.evidence
            if record.kind == EvidenceKind.repair.value
        ]
        if not attempts:
            return None
        if policy_decision and policy_decision.state.value == "reject":
            outcome = RepairOutcome.failed
        elif attempts[-1].output_code:
            outcome = RepairOutcome.succeeded
        else:
            outcome = RepairOutcome.attempted
        return RepairResult(
            outcome=outcome,
            attempts=attempts,
            final_attempt_number=attempts[-1].attempt_number,
            metrics={"reconstructed_from_evidence": True},
        )

    def queue_backlog_summary(self) -> dict[str, int | bool]:
        queued = self.session.scalar(
            select(func.count()).select_from(RunRecord).where(
                RunRecord.run_mode == RunMode.advanced.value,
                RunRecord.status == RunLifecycleStatus.queued.value,
            )
        ) or 0
        running = self.session.scalar(
            select(func.count()).select_from(RunRecord).where(
                RunRecord.run_mode == RunMode.advanced.value,
                RunRecord.status == RunLifecycleStatus.running.value,
            )
        ) or 0
        queued_count = int(queued)
        running_count = int(running)
        return {
            "queued": queued_count,
            "running": running_count,
            "total": queued_count + running_count,
            "has_backlog": (queued_count + running_count) > 0,
        }

    def worker_freshness(self, worker_id: str, *, stale_after_seconds: int) -> dict[str, object]:
        statement = (
            select(RunRecord.last_heartbeat_at)
            .where(RunRecord.claimed_by == worker_id, RunRecord.last_heartbeat_at.is_not(None))
            .order_by(RunRecord.last_heartbeat_at.desc())
            .limit(1)
        )
        last_heartbeat = self.session.execute(statement).scalar_one_or_none()
        if last_heartbeat is None:
            return {
                "worker_id": worker_id,
                "last_heartbeat_at": None,
                "fresh": False,
                "age_seconds": None,
                "stale_after_seconds": stale_after_seconds,
            }
        age_seconds = max(
            0.0,
            (datetime.now(timezone.utc) - last_heartbeat).total_seconds(),
        )
        return {
            "worker_id": worker_id,
            "last_heartbeat_at": last_heartbeat.isoformat(),
            "fresh": age_seconds <= stale_after_seconds,
            "age_seconds": round(age_seconds, 3),
            "stale_after_seconds": stale_after_seconds,
        }

    def _get_run(self, run_id: str) -> RunRecord:
        statement = (
            select(RunRecord)
            .where(RunRecord.id == run_id)
            .options(selectinload(RunRecord.evidence), selectinload(RunRecord.events))
        )
        run_record = self.session.execute(statement).scalar_one_or_none()
        if run_record is None:
            raise RunNotFoundError(run_id)
        return run_record
