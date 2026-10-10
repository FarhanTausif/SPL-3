import json
import math
import pytest
import httpx
from dehalu.core.settings import Settings
from dehalu.domain.models import ClarificationAnswers, InferenceResult
from dehalu.providers.llm import JudgePool, OllamaClient, post_with_retry
from dehalu.providers.uncertainty import summarize_logprobs
from dehalu.verification.inference import infer_prompt, finalize_intake


@pytest.mark.parametrize('answer', ['do it on your own', 'you decide', 'use defaults'])
def test_delegation_starts_generation(answer):
    result = finalize_intake(infer_prompt('Create a calculator. ' + answer, None, []), answer)
    assert not result.needs_clarification
    assert result.language == 'python'
    assert result.uncertain_assumptions


def test_clarification_is_bounded_and_completed_round_cannot_ask_again():
    inference = InferenceResult(language='generic', needs_clarification=True, clarification_questions=['A?', 'B?', 'A?', 'C?', 'D?'])
    result = finalize_intake(inference, 'Build something')
    assert len(result.clarification_details) == 3
    assert all(len(q.choices) == 3 and sum(c.recommended for c in q.choices) == 1 for q in result.clarification_details)
    result = finalize_intake(result, 'Build something', skip=True)
    assert result.language == 'python' and not result.needs_clarification
    assert not result.clarification_details and not result.clarification_questions


def test_bypass_preserves_explicit_language_and_requires_answer_or_skip():
    result = finalize_intake(infer_prompt('Build a calculator', 'typescript', []), 'Build a calculator', skip=True)
    assert result.language == 'typescript'
    assert ClarificationAnswers(skip_clarification=True).answers == ''
    with pytest.raises(ValueError): ClarificationAnswers(answers='  ')


def test_entropy_is_measured_and_malformed_data_is_unavailable():
    record = {'token': 'a', 'logprob': math.log(.5), 'top_logprobs': [{'logprob': math.log(.5)}, {'logprob': math.log(.25)}]}
    entropy, logs = summarize_logprobs([record, {'logprob': float('nan')}], 4)
    expected = -(.5 * math.log(.5) + .5 * math.log(.25))
    assert entropy['mean_nats'] == pytest.approx(expected)
    assert entropy['score'] == pytest.approx(expected / math.log(6))
    assert entropy['coverage'] == .25 and not entropy['full_distribution']
    assert len(logs['tokens']) == 1
    assert not summarize_logprobs([{'top_logprobs': [{'logprob': 2}]}])[0]['available']
    assert not summarize_logprobs([])[0]['available']


def test_stream_collects_probabilities_without_changing_tokens(monkeypatch):
    class Stream:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def raise_for_status(self): pass
        def iter_lines(self):
            for token in ['hello', ' world']:
                yield json.dumps({'response': token, 'logprobs': [{'token': token, 'logprob': -.1, 'top_logprobs': [{'logprob': -.1}]}]})
            yield json.dumps({'done': True, 'eval_count': 2})
    def stream(method, url, **kwargs):
        assert kwargs['json']['logprobs'] and kwargs['json']['top_logprobs'] == 5
        return Stream()
    monkeypatch.setattr(httpx, 'stream', stream)
    chunks = list(OllamaClient(Settings(allow_fake_llm=False)).stream_generate('test'))
    assert ''.join(c.text for c in chunks) == 'hello world'
    assert chunks[-1].metadata['entropy']['measured_tokens'] == 2
    assert chunks[-1].metadata['entropy']['coverage'] == 1


@pytest.mark.parametrize('status, category', [(401, 'Authentication failed'), (403, 'Model access denied'), (404, 'Model unavailable'), (429, 'Rate limit or quota exhausted')])
def test_judge_provider_errors_are_specific_and_redacted(monkeypatch, status, category):
    key = 'private-test-key'
    def fail(*args):
        response = httpx.Response(status, json={'error': f'problem {key}'}, request=httpx.Request('POST', 'https://example.com'))
        response.raise_for_status()
    monkeypatch.setattr(JudgePool, '_call_provider', fail)
    result = JudgePool(Settings(allow_fake_llm=False))._judge_one('groq', 'model', key, 'role', '{}')
    assert result.status == 'failed' and result.verdict is None
    assert category in result.explanation and key not in result.explanation


def test_retry_after_is_respected_without_unbounded_wait(monkeypatch):
    responses = iter([httpx.Response(429, headers={'retry-after': '3'}, request=httpx.Request('POST', 'https://example.com')), httpx.Response(200, request=httpx.Request('POST', 'https://example.com'))])
    monkeypatch.setattr(httpx, 'post', lambda *a, **kw: next(responses))
    sleeps = []
    monkeypatch.setattr('dehalu.providers.llm.time.sleep', sleeps.append)
    assert post_with_retry(Settings(provider_retries=1), 'https://example.com').status_code == 200
    assert sleeps == [3]


def test_dotenv_does_not_depend_on_launch_directory_and_preserves_environment(tmp_path, monkeypatch):
    import dehalu.core.settings as config
    root = tmp_path / 'project'
    (root / 'backend').mkdir(parents=True)
    (root / '.env').write_text('DEHALU_TEST_SETTING=root\nDEHALU_TEST_PROCESS=file\n')
    (root / 'backend' / '.env').write_text('DEHALU_TEST_SETTING=backend\n')
    monkeypatch.setattr(config, '__file__', str(root / 'backend/src/dehalu/core/settings.py'))
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv('DEHALU_TEST_SETTING', raising=False)
    monkeypatch.setenv('DEHALU_TEST_PROCESS', 'process')
    config._load_dotenv()
    import os
    assert os.environ['DEHALU_TEST_SETTING'] == 'backend'
    assert os.environ['DEHALU_TEST_PROCESS'] == 'process'


@pytest.mark.parametrize('flags', [[False, False, False], [True, True, True], [False, True, True]])
def test_model_intake_repairs_recommendation_flags_before_validation(flags):
    from dehalu.verification.inference import normalize_model_intake
    fallback = infer_prompt('Develop a real-time text processing web service.', None, [])
    question = 'What should text processing do?'
    payload = {'language': 'python', 'needs_clarification': False, 'clarification_questions': [question],
               'clarification_details': [{'question': question, 'choices': [
                   {'label': str(i), 'value': f'Behavior {i}', 'recommended': flag} for i, flag in enumerate(flags)]}]}
    result = normalize_model_intake(payload, fallback)
    assert result.needs_clarification
    choices = result.clarification_details[0].choices
    assert sum(c.recommended for c in choices) == 1
    assert next(i for i, c in enumerate(choices) if c.recommended) == (flags.index(True) if True in flags else 0)
    assert [c.value for c in choices] == ['Behavior 0', 'Behavior 1', 'Behavior 2']


def test_model_intake_recovers_incomplete_choices_and_detail_only_questions():
    from dehalu.verification.inference import normalize_model_intake
    fallback = infer_prompt('Build a service', None, [])
    payload = {'clarification_details': [{'question': f'Question {i}', 'choices': [{'label': 'only one'}]} for i in range(5)]}
    result = normalize_model_intake(payload, fallback)
    assert len(result.clarification_details) == 3
    assert all(len(q.choices) == 3 for q in result.clarification_details)
    assert len(result.clarification_questions) == 3


def test_model_intake_malformed_context_retains_original_requirements():
    from dehalu.verification.inference import normalize_model_intake
    fallback = infer_prompt('Build a service. Preserve user text.', None, ['No external calls'])
    result = normalize_model_intake({'language': ['invalid'], 'requirements': 42}, fallback)
    assert result.requirements == fallback.requirements
    assert result.constraints == ['No external calls']
    assert any('malformed' in value for value in result.uncertain_assumptions)


def test_structured_code_recovery_removes_model_added_markdown():
    from dehalu.providers.llm import CodeArtifact
    artifact = CodeArtifact.model_validate({'code': 'Here is repaired code:\n```python\ndef add(a, b):\n return a + b\n```\nDone.', 'assumptions': [], 'dependencies': [], 'entry_points': [], 'limitations': []})
    assert artifact.code == 'def add(a, b):\n return a + b'
    with pytest.raises(ValueError):
        CodeArtifact.model_validate({**artifact.model_dump(), 'code': '```python\nx=1\n```\n```python\ny=2\n```'})
