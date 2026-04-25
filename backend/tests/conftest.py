from __future__ import annotations

from collections.abc import AsyncGenerator, Generator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from dehalu.core.app import create_app
from dehalu.state.database import get_session
from dehalu.state.models import Base


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    SessionTesting = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    with SessionTesting() as session:
        yield session
    Base.metadata.drop_all(engine)


@pytest.fixture()
async def client(db_session: Session) -> AsyncGenerator[AsyncClient, None]:
    app = create_app()

    async def override_get_session() -> AsyncGenerator[Session, None]:
        yield db_session

    app.dependency_overrides[get_session] = override_get_session
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def anyio_backend() -> str:
    return "asyncio"
