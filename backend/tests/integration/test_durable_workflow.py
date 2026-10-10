import os
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, update
from sqlalchemy.orm import sessionmaker
from dehalu.core.settings import Settings
from dehalu.domain.models import RunCreate
from dehalu.state.models import RunJobRecord, RunEventRecord, CoVeResultRecord, ClaimRecord
from dehalu.state.repository import RunRepository
from dehalu.state.workflow import enqueue, claim_job, cancel, resume, heartbeat, sweep_expired, RunStopped
from dehalu.services.pipeline import DeHaluPipeline

pytestmark = pytest.mark.skipif('DATABASE_URL' not in os.environ, reason='Isolated PostgreSQL database required')

@pytest.fixture
def sessions(monkeypatch):
    import dehalu.services.pipeline as pipeline
    import dehalu.state.workflow as workflow
    config = Settings(allow_fake_llm=True, package_lookups=False)
    monkeypatch.setattr(pipeline, 'settings', config)
    monkeypatch.setattr(workflow, 'settings', config)
    engine = create_engine(os.environ['DATABASE_URL'])
    yield sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    engine.dispose()


def test_queue_exclusive_claim_and_claim_evidence_links(sessions):
    with sessions() as db: run = enqueue(db, RunCreate(prompt='Write Python code using an undefined helper', max_retry=0))
    def claim(owner):
        with sessions() as db: return claim_job(db, owner)
    with ThreadPoolExecutor(max_workers=2) as pool: claimed = list(pool.map(claim, ['one', 'two']))
    assert claimed.count(run.id) == 1
    with sessions() as db:
        DeHaluPipeline(db).execute(run.id)
        evidence = DeHaluPipeline(db).get_evidence(run.id)
        assert evidence.attempts
        ids = {c.id for c in evidence.attempts[0].claims}
        assert all(c.claim_id in ids for c in evidence.attempts[0].cove_results)
        stored = db.scalars(select(CoVeResultRecord).where(CoVeResultRecord.output_id == evidence.attempts[0].output.id)).all()
        assert stored and all(c.claim_id is not None for c in stored)
        events = db.scalars(select(RunEventRecord).where(RunEventRecord.run_id == run.id).order_by(RunEventRecord.sequence)).all()
        assert [e.sequence for e in events] == list(range(1, len(events)+1))
        assert events[-1].event_type == 'run_completed'


def test_cancellation_and_expired_lease(sessions):
    with sessions() as db:
        run = enqueue(db, RunCreate(prompt='Write a Python addition function'))
        assert claim_job(db, 'owner') == run.id
        assert heartbeat(db, run.id, 'owner')
        assert not heartbeat(db, run.id, 'other')
        cancel(db, run.id)
        assert not heartbeat(db, run.id, 'owner')
        DeHaluPipeline(db).execute(run.id)
        assert DeHaluPipeline(db).get_run(run.id).status == 'cancelled'
        run2 = enqueue(db, RunCreate(prompt='Write a Python addition function'))
        assert claim_job(db, 'owner') == run2.id
        db.execute(update(RunJobRecord).where(RunJobRecord.run_id == run2.id).values(lease_until=datetime.now(timezone.utc)-timedelta(seconds=5)))
        db.commit()
        assert run2.id in sweep_expired(db)
        assert DeHaluPipeline(db).get_run(run2.id).status == 'interrupted'


def test_clarification_resumes_same_run(sessions):
    with sessions() as db:
        run = enqueue(db, RunCreate(prompt='add', max_retry=0))
        DeHaluPipeline(db).execute(run.id)
        assert DeHaluPipeline(db).get_run(run.id).status == 'needs_clarification'
        resume(db, run.id, 'Use Python. Add two numeric arguments.', 'python')
        DeHaluPipeline(db).execute(run.id)
        evidence = DeHaluPipeline(db).get_evidence(run.id)
        assert evidence.run.status == 'completed' and len(evidence.attempts) == 1


def test_repair_limit_reverification_and_hash_stop(sessions):
    with sessions() as db:
        run = DeHaluPipeline(db).create_run(RunCreate(prompt='Write Python code using fake_lib_404', max_retry=2))
        evidence = DeHaluPipeline(db).get_evidence(run.id)
        assert len(evidence.attempts) == 2
        assert evidence.attempts[0].policy.decision == 'repair'
        assert evidence.attempts[1].policy.decision == 'warn'
        assert evidence.attempts[1].claims
        assert evidence.attempts[1].metrics.mihn < evidence.attempts[0].metrics.mihn
        run = DeHaluPipeline(db).create_run(RunCreate(prompt='Write Python code using fake_lib_404', max_retry=0))
        assert run.status == 'rejected'


def test_http_enqueue_replay_cancel_and_export(sessions, monkeypatch):
    from dehalu.main import create_app
    from dehalu.state.database import get_session
    import dehalu.api.routes as routes
    app = create_app()
    def db_override():
        with sessions() as db: yield db
    app.dependency_overrides[get_session] = db_override
    monkeypatch.setattr(routes, 'SessionLocal', sessions)
    with TestClient(app) as client:
        response = client.post('/api/runs', json={'prompt': 'Write a Python addition function', 'max_retry': 0})
        assert response.status_code == 202
        run_id = response.json()['id']
        assert response.json()['status'] == 'queued'
        assert client.post(f'/api/runs/{run_id}/cancel').json()['status'] == 'cancelled'
        stream = client.get(f'/api/runs/{run_id}/events?after=1')
        assert 'run_cancelled' in stream.text and 'run_created' not in stream.text
        assert client.get(f'/api/runs/{run_id}/export').json()['attempts'] == []
        assert client.get('/api/runs/not-a-uuid').status_code == 422
        assert client.post(f'/api/runs/{run_id}/clarification', json={'answers': 'Python'}).status_code == 409


def test_failure_retains_output_and_marks_stage_failed(sessions, monkeypatch):
    from dehalu.providers.llm import JudgePool
    def fail(*args, **kwargs): raise RuntimeError('test judge infrastructure failed')
    monkeypatch.setattr(JudgePool, 'judge', fail)
    with sessions() as db:
        run = DeHaluPipeline(db).create_run(RunCreate(prompt='Write a Python addition function', max_retry=0))
        evidence = DeHaluPipeline(db).get_evidence(run.id)
        assert run.status == 'failed'
        assert evidence.partial['output']['code'].startswith('def add')
        assert evidence.partial['claims'] and evidence.partial['coverage']
        events = db.scalars(select(RunEventRecord).where(RunEventRecord.run_id == run.id)).all()
        assert any(e.payload.get('status') == 'failed' and e.payload.get('stage') == 'judge_pool' for e in events)


def test_same_code_hash_stops_repair_without_accepting_blocker(sessions, monkeypatch):
    from dehalu.providers.llm import OllamaClient
    monkeypatch.setattr(OllamaClient, 'stream_repair', lambda self, prompt: self.stream_generate('Write Python code using fake_lib_404'))
    with sessions() as db:
        run = DeHaluPipeline(db).create_run(RunCreate(prompt='Write Python code using fake_lib_404', max_retry=5))
        evidence = DeHaluPipeline(db).get_evidence(run.id)
        assert len(evidence.attempts) == 2 and run.status == 'rejected'
        assert 'Repeated code hash' in evidence.attempts[-1].policy.reason


def test_separate_worker_process_entrypoint(sessions, monkeypatch):
    import dehalu.worker as worker
    monkeypatch.setattr(worker, 'SessionLocal', sessions)
    with sessions() as db:
        run = enqueue(db, RunCreate(prompt='Write a Python addition function', max_retry=0))
        assert claim_job(db, 'worker-test') == run.id
    worker.process(run.id, 'worker-test')
    with sessions() as db:
        assert DeHaluPipeline(db).get_run(run.id).status == 'completed'
        assert db.scalar(select(RunJobRecord).where(RunJobRecord.run_id == run.id)).status == 'completed'


def test_incomplete_metadata_is_normalized_without_changing_code(sessions, monkeypatch):
    from dehalu.providers.llm import OllamaClient, LLMStreamChunk
    code = 'def add(a, b):\n    return a + b'
    def generate(self, prompt):
        yield LLMStreamChunk(text=f'```python\n{code}\n```\n{{}}')
        yield LLMStreamChunk(done=True, metadata={'entropy': {'available': False}})
    monkeypatch.setattr(OllamaClient, 'stream_generate', generate)
    monkeypatch.setattr(OllamaClient, 'structured', lambda self, system, payload, schema=None: {'assumptions': [], 'dependencies': [], 'entry_points': ['add'], 'limitations': []})
    with sessions() as db:
        run = DeHaluPipeline(db).create_run(RunCreate(prompt='Write a Python addition function', max_retry=0))
        assert run.status == 'completed'
        assert run.final_output.code == code
        assert run.final_output.metadata['metadata_normalized'] is True
        assert 'incomplete' in run.final_output.metadata['limitations'][0]


def test_repair_cannot_introduce_unverified_dependency(sessions, monkeypatch):
    from dehalu.providers.llm import OllamaClient, LLMStreamChunk
    def repair(self, prompt):
        yield LLMStreamChunk(text='```python\nimport unknown_repair_package\ndef add(a,b):\n return a+b\n```\n{"assumptions": [], "dependencies": ["unknown_repair_package"], "entry_points": ["add"], "limitations": []}')
        yield LLMStreamChunk(done=True, metadata={'entropy': {'available': False}})
    monkeypatch.setattr(OllamaClient, 'stream_repair', repair)
    with sessions() as db:
        run = DeHaluPipeline(db).create_run(RunCreate(prompt='Write Python code using fake_lib_404', max_retry=1))
        evidence = DeHaluPipeline(db).get_evidence(run.id)
        assert run.status == 'rejected'
        assert any(f.rule_id == 'repair.disallowed-dependency' for f in evidence.attempts[-1].static_findings)


@pytest.mark.parametrize('skip', [False, True])
def test_clarification_does_not_repeat_after_resume(sessions, skip):
    with sessions() as db:
        run = enqueue(db, RunCreate(prompt='add', max_retry=0))
        DeHaluPipeline(db).execute(run.id)
        assert DeHaluPipeline(db).get_run(run.id).status == 'needs_clarification'
        resume(db, run.id, '' if skip else 'do it on your own', None, skip)
    with sessions() as db:
        DeHaluPipeline(db).execute(run.id)
        evidence = DeHaluPipeline(db).get_evidence(run.id)
        assert evidence.run.status == 'completed'
        assert evidence.attempts and not evidence.run.inferred.needs_clarification
        assert RunRepository(db).get_run(run.id).run_metadata['clarification_completed'] is True


@pytest.mark.parametrize('broken_json', [False, True])
def test_malformed_model_intake_can_clarify_then_generate(sessions, monkeypatch, broken_json):
    import dehalu.services.pipeline as pipeline
    from dehalu.providers.llm import OllamaClient
    monkeypatch.setattr(pipeline, 'settings', Settings(allow_fake_llm=False, package_lookups=False))
    def structured(self, *args, **kwargs):
        if broken_json: raise ValueError('Invalid JSON response')
        return {'language': 'generic', 'needs_clarification': True,
                'clarification_questions': ['What should text processing do?'],
                'clarification_details': [{'question': 'What should text processing do?', 'choices': [
                    {'label': 'Summarize', 'value': 'Summarize text', 'recommended': True},
                    {'label': 'Search', 'value': 'Search text', 'recommended': True},
                    {'label': 'Classify', 'value': 'Classify text', 'recommended': True}]}]}
    monkeypatch.setattr(OllamaClient, 'structured', structured)
    with sessions() as db:
        run = enqueue(db, RunCreate(prompt='Develop a real-time text processing web service.', max_retry=0))
        DeHaluPipeline(db).execute(run.id)
        waiting = DeHaluPipeline(db).get_run(run.id)
        assert waiting.status == 'needs_clarification' and waiting.error is None
        assert sum(c.recommended for c in waiting.inferred.clarification_details[0].choices) == 1
        resume(db, run.id, 'Use defaults', None, True)
    monkeypatch.setattr(pipeline, 'settings', Settings(allow_fake_llm=True, package_lookups=False))
    with sessions() as db:
        DeHaluPipeline(db).execute(run.id)
        evidence = DeHaluPipeline(db).get_evidence(run.id)
        assert evidence.run.status == 'completed'
        assert evidence.attempts[0].output.code


@pytest.mark.parametrize('recovery_valid', [True, False])
def test_prose_repair_has_one_bounded_recovery_and_keeps_completed_code(sessions, monkeypatch, recovery_valid):
    from dehalu.providers.llm import OllamaClient, LLMStreamChunk
    def repair(self, prompt):
        yield LLMStreamChunk(text='Based on the evidence, processor.predict is uncertain.')
        yield LLMStreamChunk(done=True)
    calls = []
    def structured(self, system, payload, schema=None):
        calls.append(payload)
        if not recovery_valid: return {'explanation': 'Still discussing the evidence.'}
        return {'code': 'def add(a, b):\n    return a + b', 'assumptions': [], 'dependencies': [], 'entry_points': ['add'], 'limitations': [], 'repair_summary': ['Removed fake dependency']}
    monkeypatch.setattr(OllamaClient, 'stream_repair', repair)
    monkeypatch.setattr(OllamaClient, 'structured', structured)
    with sessions() as db:
        run = DeHaluPipeline(db).create_run(RunCreate(prompt='Write Python code using fake_lib_404', max_retry=1))
        evidence = DeHaluPipeline(db).get_evidence(run.id)
        assert len(calls) == 1
        assert evidence.attempts[0].output.code.startswith('import fake_lib_404')
        if recovery_valid:
            assert run.status == 'completed' and len(evidence.attempts) == 2
            repaired = evidence.attempts[1]
            assert repaired.output.metadata['format_recovered'] is True
            assert repaired.claims and repaired.output.code.startswith('def add')
            assert repaired.metrics.entropy_score is None
        else:
            assert run.status == 'failed' and len(evidence.attempts) == 1
            assert 'one format recovery attempt' in run.error
            assert evidence.partial['format_recovery_failed']
        events = db.scalars(select(RunEventRecord).where(RunEventRecord.run_id == run.id)).all()
        assert any(e.event_type == 'generation_reset' for e in events)
