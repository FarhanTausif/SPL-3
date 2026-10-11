import json
import httpx
import pytest
from dehalu.core.judges import judge_specs
from dehalu.core.settings import Settings
from dehalu.providers.llm import JudgePool, RUBRIC, build_judge_prompt
from dehalu.verification.policy import consensus_from_judges


def config(**kwargs):
    return Settings(gemini_api_key='gemini-secret', groq_api_key='groq-secret',
                    mistral_api_key=None, allow_fake_llm=False, **kwargs)


@pytest.mark.parametrize('provider', ['gemini', 'mistral'])
def test_selection(provider):
    specs = judge_specs(config(quality_safety_provider=provider))
    assert len({s.name for s in specs}) == 3
    assert specs[-1].provider == provider
    assert specs[-1].name == ('gemini (quality/safety)' if provider == 'gemini' else 'mistral')
    assert specs[-1].key == ('gemini-secret' if provider == 'gemini' else None)
    assert 'gemini-secret' not in repr(specs)


def test_invalid_selection():
    with pytest.raises(ValueError, match='QUALITY_SAFETY_PROVIDER'):
        config(quality_safety_provider='other')


def test_separate_role_calls_and_consensus(monkeypatch):
    calls = []
    def respond(self, provider, model, key, prompt):
        calls.append((provider, prompt))
        return json.dumps({'verdict': 'pass', 'score': 1, 'rubric_json': {
            name: {'score': 1, 'evidence': []} for name in RUBRIC},
            'explanation': 'Supported', 'blocking_issues': [], 'evidence_ids': [], 'repair_suggestions': []})
    monkeypatch.setattr(JudgePool, '_call_provider', respond)
    judges = JudgePool(config()).judge(build_judge_prompt('Add', 'a+b', [], [], {}))
    assert sorted(c[0] for c in calls) == ['gemini', 'gemini', 'groq']
    for role in ('requirement_alignment', 'functional_logic', 'quality_safety'):
        assert sum(c[1].startswith('Assigned role: ' + role + '\n') for c in calls) == 1
    assert all(j.status == 'ok' for j in judges)
    assert judges[-1].judge_name == 'gemini (quality/safety)'
    consensus = consensus_from_judges(judges)
    assert consensus.valid_count == 3 and consensus.final_verdict == 'pass'


def test_missing_credentials():
    judges = JudgePool(Settings(gemini_api_key=None, groq_api_key=None, mistral_api_key='unused', allow_fake_llm=False)).judge('{}')
    assert all(j.status == 'unavailable' for j in judges)
    assert consensus_from_judges(judges).valid_count == 0


def test_fake_mode(monkeypatch):
    def unexpected(*args):
        pytest.fail('Fake mode must not call providers')
    monkeypatch.setattr(JudgePool, '_call_provider', unexpected)
    judges = JudgePool(Settings(allow_fake_llm=True)).judge('{}')
    assert len({j.judge_name for j in judges}) == 3
    assert all(j.status == 'simulated' and j.verdict is None for j in judges)


def test_redaction_and_no_switch(monkeypatch):
    calls = []
    def fail(self, provider, model, key, prompt):
        calls.append(provider)
        httpx.Response(403, json={'error': {'message': key}}, request=httpx.Request('POST', 'https://example.com')).raise_for_status()
    monkeypatch.setattr(JudgePool, '_call_provider', fail)
    judges = JudgePool(config()).judge('{}')
    assert sorted(calls) == ['gemini', 'gemini', 'groq']
    assert '[redacted]' in judges[-1].explanation
    assert 'gemini-secret' not in judges[-1].explanation


def test_malformed_response(monkeypatch):
    monkeypatch.setattr(JudgePool, '_call_provider', lambda *args: '{}')
    judges = JudgePool(config()).judge('{}')
    assert all(j.status == 'failed' for j in judges)
    assert consensus_from_judges(judges).valid_count == 0
