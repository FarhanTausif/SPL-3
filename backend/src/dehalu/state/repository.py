from __future__ import annotations

from collections import Counter
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
    RunDetail,
    RunResponse,
    SandboxResult,
    StaticFinding,
    VerificationEvidence,
)
from dehalu.state.models import EvidenceRecord, RunRecord


class RunNotFoundError(ValueError):
    pass


class RunRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_run(
        self,
        normalized_request: NormalizedRequest,
        coder_output: CoderOutput,
        extracted_claims: list[ExtractedClaim],
        static_findings: list[StaticFinding],
        sandbox_result: SandboxResult,
        judge_result: JudgeResult,
        cove_result: CoVeResult,
        policy_decision: PolicyDecision,
    ) -> RunResponse:
        run_id = str(uuid4())
        evidence_records = [
            EvidenceRecord(
                id=str(uuid4()),
                run_id=run_id,
                kind="claim_extraction",
                payload={
                    "claims": [claim.model_dump(mode="json") for claim in extracted_claims],
                    "claim_count": len(extracted_claims),
                },
            ),
            EvidenceRecord(
                id=str(uuid4()),
                run_id=run_id,
                kind="static_analysis",
                payload={
                    "findings": [finding.model_dump(mode="json") for finding in static_findings],
                    "finding_count": len(static_findings),
                },
            ),
            EvidenceRecord(
                id=str(uuid4()),
                run_id=run_id,
                kind="sandbox",
                payload=sandbox_result.model_dump(mode="json"),
            ),
            EvidenceRecord(
                id=str(uuid4()),
                run_id=run_id,
                kind="judge",
                payload=judge_result.model_dump(mode="json"),
            ),
            EvidenceRecord(
                id=str(uuid4()),
                run_id=run_id,
                kind="cove",
                payload=cove_result.model_dump(mode="json"),
            ),
            EvidenceRecord(
                id=str(uuid4()),
                run_id=run_id,
                kind="policy",
                payload=policy_decision.model_dump(mode="json"),
            ),
        ]
        run_record = RunRecord(
            id=run_id,
            prompt=normalized_request.prompt,
            language=normalized_request.language,
            risk_level=normalized_request.risk_level.value,
            provider=normalized_request.provider,
            status=policy_decision.state.value,
            normalized_request=normalized_request.model_dump(mode="json"),
            coder_output=coder_output.model_dump(mode="json"),
            policy_decision=policy_decision.model_dump(mode="json"),
            evidence=evidence_records,
        )
        self.session.add(run_record)
        self.session.commit()

        return RunResponse(
            run_id=run_id,
            normalized_request=normalized_request,
            coder_output=coder_output,
            extracted_claims=extracted_claims,
            static_findings=static_findings,
            sandbox_result=sandbox_result,
            judge_result=judge_result,
            cove_result=cove_result,
            policy_decision=policy_decision,
            evidence_ids=[record.id for record in evidence_records],
        )

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
