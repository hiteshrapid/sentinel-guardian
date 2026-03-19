"""
Integration test fixtures for FastAPI + SQLAlchemy/Postgres stack.
Template by Sentinel — adapt models and app import for your project.

Built by Hitesh Goyal & Sentinel
"""

import os
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

TEST_DB_URL = os.environ.get("DATABASE_URL", "")


def _get_test_db_url() -> str:
    if TEST_DB_URL:
        return TEST_DB_URL
    try:
        from testcontainers.postgres import PostgresContainer
        container = PostgresContainer("postgres:16")
        container.start()
        url = container.get_connection_url()
        return url.replace("postgresql://", "postgresql+asyncpg://")
    except Exception:
        return "sqlite+aiosqlite:///test.db"


_db_url = _get_test_db_url()
_engine = create_async_engine(_db_url, pool_size=1)
_async_session = sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with _async_session() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session) -> AsyncGenerator[AsyncClient, None]:
    from app.main import app  # <-- adjust import
    from app.deps import get_db  # <-- adjust import

    app.dependency_overrides[get_db] = lambda: db_session

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        follow_redirects=True,
    ) as ac:
        yield ac

    app.dependency_overrides.clear()
