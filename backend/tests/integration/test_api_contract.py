import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from dehalu.api.schemas import RunCreate
from dehalu.services.pipeline import DeHaluPipeline
from dehalu.state.database import Base
from dehalu.state import models  # noqa: F401


@pytest.mark.skipif("DATABASE_URL" not in os.environ, reason="Postgres DATABASE_URL is required")
def test_pipeline_persists_complete_run(monkeypatch) -> None:
    monkeypatch.setenv("DEHALU_ALLOW_FAKE_LLM", "true")
    engine = create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)
    with engine.connect() as connection:
        connection.execute(text("select 1"))
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)

    with Session() as db:
        result = DeHaluPipeline(db).create_run(
            RunCreate(prompt="Write a Python function that imports fake_lib_404.", language_hint="python", max_retry=0)
        )
        evidence = DeHaluPipeline(db).get_evidence(result.id)

    assert result.status in {"reject", "completed"}
    assert evidence is not None
    assert evidence.attempts
    assert evidence.attempts[0].judge_results
