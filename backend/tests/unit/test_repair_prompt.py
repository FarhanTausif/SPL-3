from dehalu.api.schemas import (
    AttemptEvidence,
    GeneratedOutput,
    JudgeConsensus,
    MetricResult,
    PolicyDecision,
)
from dehalu.services.pipeline import DeHaluPipeline


def test_repair_prompt_mentions_cove_and_chain_of_thought() -> None:
    attempt = AttemptEvidence(
        output=GeneratedOutput(attempt_no=1, code="import fake_lib_404", provider="ollama"),
        claims=[],
        static_findings=[],
        metrics=MetricResult(mihn=1, mahr=1, tr_s=0, entropy_score=0, hallucination_risk_score=0.8),
        judge_results=[],
        judge_consensus=JudgeConsensus(final_verdict="fail", average_score=0.2, agreement_level="high", summary="bad"),
        cove_results=[],
        policy=PolicyDecision(decision="repair", reason="bad"),
    )

    prompt = DeHaluPipeline.__new__(DeHaluPipeline)._repair_prompt("fix it", attempt)

    assert "Chain-of-Thought-style structured repair" in prompt
    assert "CoVe facts" in prompt
