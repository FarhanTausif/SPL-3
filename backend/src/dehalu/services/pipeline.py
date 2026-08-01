from __future__ import annotations

from sqlalchemy.orm import Session

from dehalu.api.schemas import AttemptEvidence, GeneratedOutput, PolicyDecision, RunCreate, RunEvidence, RunSummary
from dehalu.core.settings import settings
from dehalu.providers.llm import JudgePool, OllamaClient, build_judge_prompt
from dehalu.state.repository import RunRepository, run_to_evidence, run_to_summary
from dehalu.verification.claims import extract_claims
from dehalu.verification.cove import run_cove
from dehalu.verification.inference import infer_prompt
from dehalu.verification.metrics import compute_metrics
from dehalu.verification.policy import consensus_from_judges, decide_policy
from dehalu.verification.static_analysis import run_static_analysis
from dehalu.verification.symbols import validate_symbols


class DeHaluPipeline:
    def __init__(self, db: Session) -> None:
        self.repository = RunRepository(db)
        self.ollama = OllamaClient(settings)
        self.judges = JudgePool(settings)

    def create_run(self, request: RunCreate) -> RunSummary:
        inference = infer_prompt(request.prompt, request.language_hint, request.constraints)
        run = self.repository.create_run(
            request.prompt,
            model_name=settings.ollama_model,
            max_retry=request.max_retry,
            inference=inference,
        )
        if inference.needs_clarification:
            self.repository.save_clarification(run, "; ".join(inference.clarification_questions))
            stored = self.repository.get_run(str(run.id))
            return run_to_summary(stored or run)

        prompt = self._generation_prompt(request.prompt, inference.model_dump())
        code, explanation, entropy, logprob = self.ollama.generate(prompt)
        attempt = self._evaluate_attempt(
            prompt=request.prompt,
            language=inference.language or "generic",
            attempt_no=1,
            code=code,
            explanation=explanation,
            entropy=entropy,
            logprob=logprob,
            can_repair=request.max_retry > 0,
        )
        self.repository.save_attempt(run, attempt)

        current_policy = attempt.policy
        attempt_no = 1
        while current_policy.decision == "repair" and attempt_no <= request.max_retry:
            attempt_no += 1
            repair_prompt = self._repair_prompt(request.prompt, attempt)
            repaired_code, repaired_explanation, repaired_entropy, repaired_logprob = self.ollama.repair(repair_prompt)
            attempt = self._evaluate_attempt(
                prompt=request.prompt,
                language=inference.language or "generic",
                attempt_no=attempt_no,
                code=repaired_code,
                explanation=repaired_explanation,
                entropy=repaired_entropy,
                logprob=repaired_logprob,
                can_repair=attempt_no <= request.max_retry,
            )
            self.repository.save_attempt(run, attempt)
            current_policy = attempt.policy

        final_status = "completed" if current_policy.decision in {"accept", "warn"} else current_policy.decision
        self.repository.complete_run(run, final_status)
        stored = self.repository.get_run(str(run.id))
        return run_to_summary(stored or run)

    def get_run(self, run_id: str) -> RunSummary | None:
        run = self.repository.get_run(run_id)
        return run_to_summary(run) if run else None

    def get_evidence(self, run_id: str) -> RunEvidence | None:
        run = self.repository.get_run(run_id)
        return run_to_evidence(run) if run else None

    def _evaluate_attempt(
        self,
        *,
        prompt: str,
        language: str,
        attempt_no: int,
        code: str,
        explanation: str,
        entropy: dict,
        logprob: dict,
        can_repair: bool,
    ) -> AttemptEvidence:
        claims = extract_claims(code, explanation)
        findings = run_static_analysis(code, language)
        findings.extend(validate_symbols(code, language, claims))
        metrics = compute_metrics(code, claims, findings, entropy)
        judge_prompt = build_judge_prompt(
            prompt,
            code,
            [claim.model_dump() for claim in claims],
            [finding.model_dump() for finding in findings],
            metrics.model_dump(),
        )
        judge_results = self.judges.judge(judge_prompt, metrics.hallucination_risk_score)
        consensus = consensus_from_judges(judge_results)
        cove = run_cove(claims, findings)
        policy = decide_policy(findings, metrics, consensus, cove, can_repair=can_repair)
        return AttemptEvidence(
            output=GeneratedOutput(
                attempt_no=attempt_no,
                code=code,
                explanation=explanation,
                provider="ollama",
                entropy_summary=entropy,
                logprob_summary=logprob,
            ),
            claims=claims,
            static_findings=findings,
            metrics=metrics,
            judge_results=judge_results,
            judge_consensus=consensus,
            cove_results=cove,
            policy=policy,
        )

    def _generation_prompt(self, user_prompt: str, inference: dict) -> str:
        return (
            "Generate code for the user request. Return code in a fenced code block and briefly list assumptions.\n"
            f"Inferred context: {inference}\n"
            f"User request: {user_prompt}"
        )

    def _repair_prompt(self, user_prompt: str, attempt: AttemptEvidence) -> str:
        cove_facts = "\n".join(f"- {item.verdict}: {item.evidence}" for item in attempt.cove_results)
        static_evidence = "\n".join(f"- {item.severity} {item.rule_id}: {item.message}" for item in attempt.static_findings)
        return (
            "Use Chain-of-Thought-style structured repair internally: identify evidence-backed fixes, "
            "apply only those fixes, avoid unsupported dependencies, and return only repaired code plus a short summary. "
            "Do not reveal private reasoning.\n"
            f"Original user request: {user_prompt}\n"
            f"Failed code:\n```text\n{attempt.output.code}\n```\n"
            f"Static evidence:\n{static_evidence}\n"
            f"CoVe facts:\n{cove_facts}\n"
        )
