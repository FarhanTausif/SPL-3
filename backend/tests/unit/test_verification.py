from dehalu.verification.claims import extract_claims
from dehalu.verification.cove import run_cove
from dehalu.verification.metrics import compute_metrics
from dehalu.verification.policy import consensus_from_judges, decide_policy
from dehalu.verification.static_analysis import run_static_analysis
from dehalu.verification.symbols import validate_symbols
from dehalu.api.schemas import JudgeResult
from dehalu.api.schemas import CoVeResult, JudgeConsensus, MetricResult, StaticFinding


def test_unknown_import_and_undefined_data_produce_evidence() -> None:
    code = "import fake_lib_404\n\nresult = fake_lib_404.magic_call(data)\n"
    claims = extract_claims(code)
    findings = run_static_analysis(code, "python")
    findings.extend(validate_symbols(code, "python", claims))
    metrics = compute_metrics(code, claims, findings, {})

    assert any(f.rule_id == "symbol-indexer.unresolved-import" for f in findings)
    assert metrics.mihn >= 1
    assert metrics.hallucination_risk_score > 0


def test_missing_plausible_import_warns_instead_of_hard_rejecting() -> None:
    code = "import plausible_package_for_demo\n"
    claims = extract_claims(code)
    findings = validate_symbols(code, "python", claims)

    assert claims[0].status == "uncertain"
    assert findings[0].severity == "warning"


def test_unsafe_operation_triggers_sast_fallback() -> None:
    findings = run_static_analysis("import os\nos.system('rm -rf /tmp/x')\n", "python")

    assert any(f.rule_id.startswith("semgrep.") for f in findings)


def test_repetition_score_detects_degenerated_code() -> None:
    code = "print('x')\nprint('x')\nprint('x')\n"
    metrics = compute_metrics(code, [], [], {})

    assert metrics.tr_s > 0


def test_judge_consensus_and_policy_repair() -> None:
    judges = [
        JudgeResult(judge_name="gemini", judge_model="m", verdict="fail", score=0.2, explanation="bad"),
        JudgeResult(judge_name="groq", judge_model="m", verdict="fail", score=0.3, explanation="bad"),
        JudgeResult(judge_name="mistral", judge_model="m", verdict="warn", score=0.5, explanation="uncertain"),
    ]
    consensus = consensus_from_judges(judges)
    policy = decide_policy([], compute_metrics("", [], [], {"score": 0.8}), consensus, [], can_repair=True)

    assert consensus.final_verdict == "fail"
    assert policy.decision == "repair"


def test_policy_warns_after_retry_when_only_soft_risk_remains() -> None:
    policy = decide_policy(
        findings=[
            StaticFinding(
                rule_id="symbol-indexer.invalid-reference",
                severity="warning",
                message="Reference could not be locally verified.",
                location="line 1",
                evidence_source="Symbol Indexer/API Validator",
            )
        ],
        metrics=MetricResult(mihn=1, mahr=0.2, tr_s=0, entropy_score=0, hallucination_risk_score=0.4),
        consensus=JudgeConsensus(final_verdict="warn", average_score=0.7, agreement_level="medium", summary="warn"),
        cove=[CoVeResult(verdict="uncertain", evidence="not locally verifiable", confidence=0.5)],
        can_repair=False,
    )

    assert policy.decision == "warn"


def test_policy_warns_without_spending_repairs_on_missing_evidence() -> None:
    policy = decide_policy(
        findings=[
            StaticFinding(
                rule_id="symbol-indexer.invalid-reference",
                severity="warning",
                message="Reference could not be locally verified.",
                location="line 1",
                evidence_source="Symbol Indexer/API Validator",
            )
        ],
        metrics=MetricResult(mihn=1, mahr=0.2, tr_s=0, entropy_score=0, hallucination_risk_score=0.4),
        consensus=JudgeConsensus(final_verdict="warn", average_score=0.7, agreement_level="medium", summary="warn"),
        cove=[CoVeResult(verdict="uncertain", evidence="not locally verifiable", confidence=0.5)],
        can_repair=True,
    )

    assert policy.decision == "warn"


def test_policy_still_rejects_fake_import_after_retry_limit() -> None:
    policy = decide_policy(
        findings=[
            StaticFinding(
                rule_id="symbol-indexer.unresolved-import",
                severity="error",
                message="Dependency fake_lib_404 could not be resolved.",
                location="line 1",
                evidence_source="Symbol Indexer/API Validator",
            )
        ],
        metrics=MetricResult(mihn=1, mahr=1, tr_s=0, entropy_score=0, hallucination_risk_score=0.7),
        consensus=JudgeConsensus(final_verdict="warn", average_score=0.5, agreement_level="medium", summary="warn"),
        cove=[CoVeResult(verdict="unsupported", evidence="fake import", confidence=0.9)],
        can_repair=False,
    )

    assert policy.decision == "reject"


def test_cove_does_not_infer_nonexistence_from_a_package_name() -> None:
    claims = extract_claims("import fake_lib_404\n")
    findings = validate_symbols("import fake_lib_404\n", "python", claims)
    cove = run_cove(claims, findings)

    assert cove[0].verdict == "uncertain"
