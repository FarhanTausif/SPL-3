from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from dehalu.schemas import (
    CoderOutput,
    CoVeResult,
    ExtractedClaim,
    JudgeResult,
    NormalizedRequest,
    PolicyDecision,
    RepairOutcome,
    RepairResult,
    RunDetail,
    RunResponse,
    SandboxResult,
    StaticFinding,
    VerificationEvidence,
)
from dehalu.state.models import EvidenceRecord, RunRecord


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

    def create_run(
        self,
        normalized_request: NormalizedRequest,
        final_attempt: EvaluationBundle,
        repair_result: RepairResult,
        original_attempt: EvaluationBundle | None = None,
    ) -> RunResponse:
        run_id = str(uuid4())
        evidence_records: list[EvidenceRecord] = []
        if original_attempt is not None:
            evidence_records.extend(self._build_attempt_evidence(run_id, original_attempt))

        if repair_result.outcome != RepairOutcome.skipped:
            for repair_attempt in repair_result.attempts:
                evidence_records.append(
                    EvidenceRecord(
                        id=str(uuid4()),
                        run_id=run_id,
                        kind="repair",
                        payload=repair_attempt.model_dump(mode="json"),
                    )
                )

        evidence_records.extend(self._build_attempt_evidence(run_id, final_attempt))
        run_record = RunRecord(
            id=run_id,
            prompt=normalized_request.prompt,
            language=normalized_request.language,
            risk_level=normalized_request.risk_level.value,
            provider=normalized_request.provider,
            status=final_attempt.policy_decision.state.value,
            normalized_request=normalized_request.model_dump(mode="json"),
            coder_output=final_attempt.coder_output.model_dump(mode="json"),
            policy_decision=final_attempt.policy_decision.model_dump(mode="json"),
            evidence=evidence_records,
        )
        self.session.add(run_record)
        self.session.commit()

        return RunResponse(
            run_id=run_id,
            normalized_request=normalized_request,
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

    def _build_attempt_evidence(self, run_id: str, attempt: EvaluationBundle) -> list[EvidenceRecord]:
        attempt_metadata = {
            "attempt_number": attempt.attempt_number,
            "attempt_stage": attempt.attempt_stage,
        }
        return [
            EvidenceRecord(
                id=str(uuid4()),
                run_id=run_id,
                kind="claim_extraction",
                payload={
                    **attempt_metadata,
                    "claims": [claim.model_dump(mode="json") for claim in attempt.extracted_claims],
                    "claim_count": len(attempt.extracted_claims),
                },
            ),
            EvidenceRecord(
                id=str(uuid4()),
                run_id=run_id,
                kind="static_analysis",
                payload={
                    **attempt_metadata,
                    "findings": [finding.model_dump(mode="json") for finding in attempt.static_findings],
                    "finding_count": len(attempt.static_findings),
                },
            ),
            EvidenceRecord(
                id=str(uuid4()),
                run_id=run_id,
                kind="sandbox",
                payload={
                    **attempt_metadata,
                    **attempt.sandbox_result.model_dump(mode="json"),
                },
            ),
            EvidenceRecord(
                id=str(uuid4()),
                run_id=run_id,
                kind="judge",
                payload={
                    **attempt_metadata,
                    **attempt.judge_result.model_dump(mode="json"),
                },
            ),
            EvidenceRecord(
                id=str(uuid4()),
                run_id=run_id,
                kind="cove",
                payload={
                    **attempt_metadata,
                    **attempt.cove_result.model_dump(mode="json"),
                },
            ),
            EvidenceRecord(
                id=str(uuid4()),
                run_id=run_id,
                kind="policy",
                payload={
                    **attempt_metadata,
                    **attempt.policy_decision.model_dump(mode="json"),
                },
            ),
        ]

    def get_run_detail(self, run_id: str) -> RunDetail:
        run_record = self._get_run(run_id)
        evidence_summary = Counter(record.kind for record in run_record.evidence)
        return RunDetail(
            run_id=run_record.id,
            created_at=run_record.created_at,
            normalized_request=NormalizedRequest.model_validate(run_record.normalized_request),
            policy_decision=PolicyDecision.model_validate(run_record.policy_decision),
            evidence_summary=dict(evidence_summary),
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

    def _get_run(self, run_id: str) -> RunRecord:
        statement = (
            select(RunRecord)
            .where(RunRecord.id == run_id)
            .options(selectinload(RunRecord.evidence))
        )
        run_record = self.session.execute(statement).scalar_one_or_none()
        if run_record is None:
            raise RunNotFoundError(run_id)
        return run_record
