from pathlib import Path
import runpy
import sys
import httpx
import pytest
from dehalu.core.settings import Settings
from dehalu.domain.models import JudgeResult


def script():
    return runpy.run_path(str(Path(__file__).resolve().parents[2] / 'scripts/provider_readiness.py'))['main']


def test_catalog_checks_only_active_providers_once(monkeypatch, capsys):
    main = script()
    monkeypatch.setitem(main.__globals__, 'settings', Settings(gemini_api_key='secret', groq_api_key='secret', mistral_api_key='unused'))
    monkeypatch.setattr(sys, 'argv', ['provider_readiness.py'])
    calls = []
    def get(url, **kwargs):
        calls.append(url)
        return httpx.Response(200, json={'data': [], 'models': []})
    monkeypatch.setattr(httpx, 'get', get)
    assert main() == 0
    assert len(calls) == 2 and all('mistral' not in url for url in calls)
    output = capsys.readouterr().out
    assert 'quality_safety' in output and 'secret' not in output


def test_live_reports_failure_and_checks_each_role(monkeypatch, capsys):
    main = script()
    monkeypatch.setitem(main.__globals__, 'settings', Settings(gemini_api_key=None, groq_api_key=None, allow_fake_llm=False))
    monkeypatch.setattr(sys, 'argv', ['provider_readiness.py', '--live'])
    calls = []
    class Pool:
        def __init__(self, settings): pass
        def _judge_one(self, provider, model, key, role, prompt, name):
            calls.append(role)
            return JudgeResult(judge_name=name, judge_model=model, role=role, status='unavailable', explanation='Missing credentials')
    monkeypatch.setitem(main.__globals__, 'JudgePool', Pool)
    assert main() == 1
    assert calls == ['requirement_alignment', 'functional_logic', 'quality_safety']
    assert 'status=unavailable' in capsys.readouterr().out


def test_live_rejects_fake_mode(monkeypatch):
    main = script()
    monkeypatch.setitem(main.__globals__, 'settings', Settings(allow_fake_llm=True))
    monkeypatch.setattr(sys, 'argv', ['provider_readiness.py', '--live'])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 2
