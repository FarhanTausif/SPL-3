import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from dehalu.api import routes
from dehalu.core.judges import judge_specs
from dehalu.core.settings import Settings


@pytest.mark.parametrize('provider', ['gemini', 'mistral'])
def test_health_describes_active_roles(monkeypatch, provider):
    config = Settings(quality_safety_provider=provider, gemini_api_key='test', groq_api_key='test',
                      mistral_api_key=None, allow_fake_llm=True)
    monkeypatch.setattr(routes, 'settings', config)
    class DB:
        def execute(self, query): pass
    app = FastAPI()
    app.include_router(routes.router)
    app.dependency_overrides[routes.get_session] = lambda: DB()
    response = TestClient(app).get('/api/health')
    assert response.status_code == 200
    judges = response.json()['judges']
    specs = judge_specs(config)
    assert list(judges) == [s.name for s in specs]
    for spec in specs:
        assert judges[spec.name]['provider'] == spec.provider
        assert judges[spec.name]['role'] == spec.role
        assert judges[spec.name]['model'] == spec.model
        assert judges[spec.name]['configured'] == bool(spec.key)
