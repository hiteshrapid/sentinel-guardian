# FastAPI + SQLAlchemy/Postgres Context

> Stack-specific patterns for testing FastAPI applications using SQLAlchemy with PostgreSQL.
> Load this context when the target repo uses `from fastapi` + `sqlalchemy`.

## Stack Summary

- **Framework:** FastAPI (async)
- **ORM:** SQLAlchemy 2.0 (async)
- **Database:** PostgreSQL
- **Package Manager:** pip (requirements.txt or pyproject.toml)
- **Test Runner:** pytest + pytest-asyncio
- **Auth Pattern:** JWT Bearer tokens
- **App Entry:** `create_app()` factory pattern

## Key Differences from Generic Defaults

This IS the generic default stack. No overrides needed.

## Install Dependencies

```bash
pip install \
  pytest pytest-asyncio pytest-cov pytest-xdist pytest-mock \
  httpx "testcontainers[postgres]" \
  openapi-spec-validator jsonschema pyyaml \
  pip-audit safety factory-boy faker ruff mypy
```

## Auth in Tests

```python
from tests.helpers.auth_helpers import generate_auth_token

token = generate_auth_token("user-1", role="user")
headers = {"Authorization": f"Bearer {token}"}
res = await client.get("/api/users/me", headers=headers)
```

## DB Setup — Integration Tests (Testcontainers Postgres)

```python
import os
import pytest
from testcontainers.postgres import PostgresContainer

@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:16-alpine") as pg:
        os.environ["DATABASE_URL"] = pg.get_connection_url()
        _run_migrations(pg.get_connection_url())
        yield pg

def _run_migrations(url: str) -> None:
    from alembic.config import Config
    from alembic import command
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(alembic_cfg, "head")
```

## Integration Test conftest.py

```python
import os
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

@pytest_asyncio.fixture(scope="module")
async def client(postgres_container):
    from app.main import create_app
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

@pytest_asyncio.fixture(autouse=True)
async def clean_db(postgres_container):
    yield
    import asyncpg
    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    await conn.execute("TRUNCATE users, items, orders CASCADE")
    await conn.close()
```

## Models (SQLAlchemy)

```python
from sqlalchemy import Column, String, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base
import uuid

class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="user")
    created_at = Column(DateTime, server_default=func.now())
```

## Repository Pattern

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_by_email(self, email: str):
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def create(self, **kwargs):
        user = User(**kwargs)
        self.session.add(user)
        await self.session.commit()
        return user
```

## CI Environment Variables

```yaml
env:
  DATABASE_URL: postgresql://test:test@localhost:5432/test_db
  JWT_SECRET: test-jwt-secret-key
  REDIS_URL: redis://localhost:6379
```
