from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.orm import Session, selectinload

from dehalu.api.schemas import (
    AttemptEvidence,
    Claim,
    CoVeResult,
    GeneratedOutput,
    InferenceResult,
    JudgeConsensus,
    JudgeResult,
    MetricResult,
    PolicyDecision,
    RunEvidence,
    RunSummary,
    StaticFinding,
)
from dehalu.state.models import (
    ClaimRecord,
    CoVeResultRecord,
    GeneratedOutputRecord,
    JudgeConsensusRecord,
    JudgeResultRecord,
    MetricResultRecord,
    PolicyDecisionRecord,
    RunRecord,
    SessionRecord,
    StaticFindingRecord,
    RunJobRecord, RunEventRecord,
)


class RunRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_session(self) -> SessionRecord:
        record = SessionRecord()
        self.db.add(record)
        self.db.flush()
        return record

    def create_run(self, prompt: str, model_name: str, max_retry: int, inference: InferenceResult) -> RunRecord:
        session = self.create_session()
        run = RunRecord(
            session_id=session.id,
            prompt=prompt,
            inferred_language=inference.language,
            model_name=model_name,
            status="created",
            max_retry=max_retry,
            run_metadata={"inference": inference.model_dump()},
        )
        self.db.add(run)
        self.db.flush()
        return run

    def save_attempt(
        self,
        run: RunRecord,
        evidence: AttemptEvidence,
    ) -> GeneratedOutputRecord:
        output = GeneratedOutputRecord(
            id=UUID(evidence.output.id),
            run_id=run.id,
            attempt_no=evidence.output.attempt_no,
            code=evidence.output.code,
            explanation=evidence.output.explanation,
            provider=evidence.output.provider,
            entropy_summary=evidence.output.entropy_summary,
            logprob_summary=evidence.output.logprob_summary,
        )
        self.db.add(output)
        self.db.flush()
        claim_id_map: dict[str, UUID] = {}
        for index, claim in enumerate(evidence.claims):
            record = ClaimRecord(
                id=UUID(claim.id),
                output_id=output.id,
                claim_type=claim.claim_type,
                claim_text=claim.claim_text,
                location=claim.location,
                status=claim.status,
            )
            self.db.add(record)
            self.db.flush()
            claim.id = str(record.id)
            claim_id_map[claim.id] = record.id

        for finding in evidence.static_findings:
            self.db.add(
                StaticFindingRecord(
                    id=UUID(finding.id),
                    output_id=output.id,
                    rule_id=finding.rule_id,
                    severity=finding.severity,
                    message=finding.message,
                    location=finding.location,
                    evidence_source=finding.evidence_source,
                )
            )
        self.db.add(
            MetricResultRecord(
                output_id=output.id,
                mihn=evidence.metrics.mihn,
                mahr=evidence.metrics.mahr,
                tr_s=evidence.metrics.tr_s,
                entropy_score=evidence.metrics.entropy_score,
                hallucination_risk_score=evidence.metrics.hallucination_risk_score,
            )
        )
        for judge in evidence.judge_results:
            self.db.add(
                JudgeResultRecord(
                    output_id=output.id,
                    judge_name=judge.judge_name,
                    judge_model=judge.judge_model,
                    verdict=judge.verdict or "unavailable",
                    score=judge.score,
                    rubric_json=judge.rubric_json,
                    explanation=judge.explanation,
                )
            )
        self.db.add(
            JudgeConsensusRecord(
                output_id=output.id,
                final_verdict=evidence.judge_consensus.final_verdict,
                average_score=evidence.judge_consensus.average_score,
                agreement_level=evidence.judge_consensus.agreement_level,
                summary=evidence.judge_consensus.summary,
            )
        )
        for index, cove in enumerate(evidence.cove_results):
            self.db.add(
                CoVeResultRecord(
                    output_id=output.id,
                    claim_id=claim_id_map.get(cove.claim_id),
                    verdict=cove.verdict,
                    evidence=cove.evidence,
                    confidence=cove.confidence,
                )
            )
        self.db.add(
            PolicyDecisionRecord(
                run_id=run.id,
                output_id=output.id,
                decision=evidence.policy.decision,
                reason=evidence.policy.reason,
            )
        )
        evidence.output.id = str(output.id)
        output.evidence_payload = evidence.model_dump(mode="json")
        self.db.flush()
        self.db.commit()
        return output

    def save_clarification(self, run: RunRecord, reason: str) -> None:
        run.status = "needs_clarification"
        run.completed_at = None
        self.db.add(PolicyDecisionRecord(run_id=run.id, output_id=None, decision="needs_clarification", reason=reason))
        self.db.commit()

    def complete_run(self, run: RunRecord, status: str) -> None:
        run.status = status
        run.completed_at = datetime.now(timezone.utc)
        self.db.commit()

    def get_run(self, run_id: str) -> RunRecord | None:
        try:
            parsed_id = UUID(run_id)
        except ValueError:
            return None
        self.db.expire_all()
        statement = (
            select(RunRecord)
            .where(RunRecord.id == parsed_id)
            .options(
                selectinload(RunRecord.outputs).selectinload(GeneratedOutputRecord.claims),
                selectinload(RunRecord.outputs).selectinload(GeneratedOutputRecord.static_findings),
                selectinload(RunRecord.outputs).selectinload(GeneratedOutputRecord.metric_result),
                selectinload(RunRecord.outputs).selectinload(GeneratedOutputRecord.judge_results),
                selectinload(RunRecord.outputs).selectinload(GeneratedOutputRecord.judge_consensus),
                selectinload(RunRecord.outputs).selectinload(GeneratedOutputRecord.cove_results),
                selectinload(RunRecord.outputs).selectinload(GeneratedOutputRecord.policy_decisions),
                selectinload(RunRecord.policy_decisions),
            )
        )
        return self.db.execute(statement).scalar_one_or_none()


def run_to_summary(run: RunRecord) -> RunSummary:
    outputs = sorted(run.outputs, key=lambda item: item.attempt_no)
    final_output = _output_to_schema(outputs[-1]) if outputs else None
    policy_record = _latest_policy(run)
    return RunSummary(
        id=str(run.id),
        status=run.status,
        prompt=run.prompt,
        inferred=InferenceResult(**run.run_metadata.get("inference", {})),
        model_name=run.model_name,
        max_retry=run.max_retry,
        final_output=final_output,
        policy_decision=_policy_to_schema(policy_record) if policy_record else None,
        created_at=run.created_at, completed_at=run.completed_at, error=run.run_metadata.get("error"),
    )


def run_to_evidence(run: RunRecord) -> RunEvidence:
    return RunEvidence(
        run=run_to_summary(run),
        attempts=[_attempt_to_schema(output) for output in sorted(run.outputs, key=lambda item: item.attempt_no)],
        partial=run.run_metadata.get("partial", {}),
    )


def _attempt_to_schema(output: GeneratedOutputRecord) -> AttemptEvidence:
    if output.evidence_payload:
        return AttemptEvidence.model_validate(output.evidence_payload)
    policy = sorted(output.policy_decisions, key=lambda item: item.created_at)[-1] if output.policy_decisions else None
    return AttemptEvidence(
        output=_output_to_schema(output),
        claims=[
            Claim(id=str(item.id), claim_type=item.claim_type, claim_text=item.claim_text, location=item.location, status=item.status)
            for item in output.claims
        ],
        static_findings=[
            StaticFinding(
                id=str(item.id),
                rule_id=item.rule_id,
                severity=item.severity,
                message=item.message,
                location=item.location,
                evidence_source=item.evidence_source,
            )
            for item in output.static_findings
        ],
        metrics=MetricResult(
            mihn=output.metric_result.mihn if output.metric_result else 0,
            mahr=output.metric_result.mahr if output.metric_result else 0,
            tr_s=output.metric_result.tr_s if output.metric_result else 0,
            entropy_score=None,
            version="legacy",
            hallucination_risk_score=output.metric_result.hallucination_risk_score if output.metric_result else 0,
        ),
        judge_results=[
            JudgeResult(
                judge_name=item.judge_name,
                judge_model=item.judge_model,
                verdict=item.verdict if item.verdict in {"pass", "warn", "fail"} else None,
                status="unavailable",
                score=item.score,
                rubric_json=item.rubric_json,
                explanation=item.explanation,
            )
            for item in output.judge_results
        ],
        judge_consensus=JudgeConsensus(
            final_verdict=output.judge_consensus.final_verdict if output.judge_consensus else "warn",
            average_score=output.judge_consensus.average_score if output.judge_consensus else 0.5,
            agreement_level=output.judge_consensus.agreement_level if output.judge_consensus else "none",
            summary=output.judge_consensus.summary if output.judge_consensus else "No consensus stored.",
        ),
        cove_results=[
            CoVeResult(claim_id=str(item.claim_id) if item.claim_id else None, verdict=item.verdict, evidence=item.evidence, confidence=item.confidence)
            for item in output.cove_results
        ],
        policy=_policy_to_schema(policy) if policy else PolicyDecision(decision="warn", reason="No policy stored."),
    )


def _output_to_schema(output: GeneratedOutputRecord) -> GeneratedOutput:
    if output.evidence_payload:
        return GeneratedOutput.model_validate(output.evidence_payload["output"])
    return GeneratedOutput(
        id=str(output.id),
        metadata={"provenance": "legacy-prototype"},
        attempt_no=output.attempt_no,
        code=output.code,
        explanation=output.explanation,
        provider=output.provider,
        entropy_summary=output.entropy_summary,
        logprob_summary=output.logprob_summary,
    )


def _latest_policy(run: RunRecord) -> PolicyDecisionRecord | None:
    if run.policy_decisions:
        return sorted(run.policy_decisions, key=lambda item: item.created_at)[-1]
    return None


def _policy_to_schema(policy: PolicyDecisionRecord) -> PolicyDecision:
    if policy.output is not None and policy.output.evidence_payload:
        return PolicyDecision.model_validate(policy.output.evidence_payload["policy"])
    return PolicyDecision(decision=policy.decision, reason=policy.reason)
