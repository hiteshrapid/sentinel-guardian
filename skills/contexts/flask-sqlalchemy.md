# Flask + SQLAlchemy/Postgres Context

> Lighter context — focuses on differences from the FastAPI + SQLAlchemy baseline.
> Load this context when the target repo uses `from flask`.

## Stack Summary

- **Framework:** Flask (sync)
- **ORM:** SQLAlchemy / Flask-SQLAlchemy
- **Database:** PostgreSQL
- **Package Manager:** pip
- **Test Runner:** pytest
- **Auth Pattern:** Flask-Login or JWT (flask-jwt-extended)
- **App Entry:** `create_app()` factory

## Key Differences from FastAPI Default

| FastAPI Default | Flask |
|---|---|
| Async (httpx + ASGITransport) | Sync (app.test_client()) |
| pytest-asyncio required | Not needed |
| Pydantic for validation | Marshmallow / WTForms |
| OpenAPI at /openapi.json | Flasgger at /apispec_1.json |

## Test Client Setup

```python
import os
import pytest
from testcontainers.postgres import PostgresContainer

@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:16-alpine") as pg:
        os.environ["DATABASE_URL"] = pg.get_connection_url()
        yield pg

@pytest.fixture(scope="module")
def client(postgres_container):
    from app import create_app
    app = create_app(testing=True)
    with app.test_client() as c:
        yield c

@pytest.fixture(autouse=True)
def clean_db(postgres_container):
    yield
    from app.extensions import db
    for table in reversed(db.metadata.sorted_tables):
        db.session.execute(table.delete())
    db.session.commit()
```

## Integration Test Pattern

```python
def test_create_user_201(client):
    res = client.post("/api/users", json={"email": "a@b.com", "password": "x"})
    assert res.status_code == 201
    assert res.get_json()["email"] == "a@b.com"

def test_create_user_409_duplicate(client):
    client.post("/api/users", json={"email": "dup@t.com", "password": "x"})
    res = client.post("/api/users", json={"email": "dup@t.com", "password": "y"})
    assert res.status_code == 409
```
