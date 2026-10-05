import pytest
from dehalu.domain.models import Claim, StaticFinding
from dehalu.core.settings import Settings
from dehalu.providers.llm import OllamaClient, JudgePool, validate_artifact
from dehalu.verification.cove import run_cove, merge_semantic_checks
from dehalu.verification.metrics import compute_metrics
from dehalu.verification.policy import consensus_from_judges


def test_unchecked_claim_is_uncertain_not_supported():
    claim = Claim(claim_type='behavior', claim_text='Always correct')
    assert run_cove([claim], [])[0].verdict == 'uncertain'


def test_static_contradiction_cannot_be_overridden_by_semantic_check():
    claim = Claim(claim_type='behavior', claim_text='Safe')
    finding = StaticFinding(rule_id='unsafe', severity='error', message='unsafe', evidence_source='test', claim_ids=[claim.id])
    results = run_cove([claim], [finding])
    merged = merge_semantic_checks([claim], results, [{'claim_id': claim.id, 'verdict': 'supported', 'confidence': 1, 'evidence': 'confident', 'evidence_ids': [finding.id]}], [finding])
    assert merged[0].verdict == 'unsupported'


def test_missing_judges_do_not_produce_passing_verdicts():
    judges = JudgePool(Settings(gemini_api_key=None, groq_api_key=None, mistral_api_key=None, allow_fake_llm=False)).judge('{}')
    assert all(j.verdict is None and j.score is None for j in judges)
    assert consensus_from_judges(judges).valid_count == 0


def test_metrics_separate_unsupported_uncertain_and_unavailable_entropy():
    metrics = compute_metrics('x = 1', [Claim(claim_type='api', claim_text='a', status='unsupported'), Claim(claim_type='api', claim_text='b', status='uncertain')], [], {'available': False})
    assert metrics.mihn == 1 and metrics.mahr == 1
    assert metrics.unsupported_count == metrics.uncertain_count == 1
    assert metrics.entropy_score is None

@pytest.mark.parametrize('raw', ['', 'plain code', '```python\n```\n{}', '```python\nx=1\n```\n```python\ny=2\n```\n{}', '```python\nx=1\n```\nnot json', '```python\nx=1\n```\n{"dependencies": "bad"}'])
def test_invalid_artifacts_are_rejected(raw):
    with pytest.raises(ValueError): validate_artifact(raw, 'python')


def test_language_conflict_is_rejected():
    with pytest.raises(ValueError): validate_artifact('```javascript\nlet x=1;\n```\n{}', 'python')


def test_accept_requires_full_judge_and_analyzer_coverage():
    from dehalu.domain.models import JudgeConsensus, CoVeResult, AnalyzerCoverage
    from dehalu.verification.policy import decide_policy
    consensus = JudgeConsensus(final_verdict='pass', average_score=1, valid_count=3, agreement_level='high', summary='all pass')
    checks = [CoVeResult(claim_id='claim', verdict='supported', evidence='direct', confidence=1)]
    coverage = [AnalyzerCoverage(analyzer='parser', language='python', status='available', detail='complete')]
    metrics = compute_metrics('x=1', [], [], {})
    assert decide_policy([], metrics, consensus, checks, can_repair=True, coverage=coverage).decision == 'accept'
    coverage[0].status = 'partial'
    assert decide_policy([], metrics, consensus, checks, can_repair=True, coverage=coverage).decision == 'warn'


def test_missing_metadata_fields_are_not_silently_accepted():
    with pytest.raises(ValueError, match='required fields'):
        validate_artifact('```python\nx=1\n```\n{}', 'python')
