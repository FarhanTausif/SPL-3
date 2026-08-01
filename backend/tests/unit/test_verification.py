from dehalu.verification.claims import extract_claims
from dehalu.verification.cove import run_cove
from dehalu.verification.metrics import compute_metrics
from dehalu.verification.policy import consensus_from_judges, decide_policy
from dehalu.verification.static_analysis import run_static_analysis
from dehalu.verification.symbols import validate_symbols
from dehalu.api.schemas import JudgeResult


def test_fake_import_triggers_symbol_finding_and_metrics() -> None:
    code = "import fake_lib_404\n\nresult = fake_lib_404.magic_call(data)\n"
    claims = extract_claims(code)
    findings = run_static_analysis(code, "python")
    findings.extend(validate_symbols(code, "python", claims))
    metrics = compute_metrics(code, claims, findings, {})

    assert any(f.rule_id == "symbol-indexer.unresolved-import" for f in findings)
    assert metrics.mihn >= 1
    assert metrics.hallucination_risk_score > 0


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


def test_cove_maps_claim_statuses() -> None:
    claims = extract_claims("import fake_lib_404\n")
    findings = validate_symbols("import fake_lib_404\n", "python", claims)
    cove = run_cove(claims, findings)

    assert cove[0].verdict == "unsupported"
