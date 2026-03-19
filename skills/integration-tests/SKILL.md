---
name: integration-tests
description: >
  Implement production-ready integration tests for a backend application. Use this skill
  when the user wants to test full HTTP request → service → database flows, spin up a real Postgres
  database with Testcontainers, write httpx endpoint tests, test authentication and authorization
  on real endpoints, or verify DB state after mutations. Trigger when the user mentions "integration
  tests", "httpx tests", "test my API endpoints", "Testcontainers", "test my
  FastAPI/Flask/Django routes", "endpoint tests with real DB", "test authentication flow",
  or "request-to-DB integration test". Always use this skill before writing any integration
  test — it contains the full setup and verification checklist.
---

# Integration Tests Skill

## Stack Adaptation

Before writing any tests, detect the project's stack and load the matching context:

| Signal | Context File |
|--------|-------------|
| `from fastapi` + `beanie`/`motor` | `contexts/fastapi-beanie.md` |
| `from fastapi` + `sqlalchemy` | `contexts/fastapi-sqlalchemy.md` |
| `from flask` | `contexts/flask-sqlalchemy.md` |
| `from django` | `contexts/django-orm.md` |
| `package.json` + `next` + `prisma` | `contexts/nextjs-prisma.md` |

Read the context file FIRST. It tells you: package manager, test runner, auth pattern, ORM, DB setup for tests, and stack-specific code patterns.

If the stack doesn't match any context, analyze the repo and create a new context before proceeding.

---

You are an expert backend QA engineer. Your mission: implement production-ready integration tests
for a backend application using httpx + Testcontainers with a real database.

**Integration tests answer: "Does the full HTTP → service → DB flow work correctly?"**
They test real routing, real DB queries, real validation — no mocking of I/O layers.

---

## Phase 1 — Audit the Repo

```bash
python3 -c "
import importlib
for pkg in ['fastapi','flask','django','sqlalchemy','asyncpg','httpx','testcontainers']:
    try: m=importlib.import_module(pkg); print(f'FOUND: {pkg} @ {getattr(m,\"__version__\",\"?\")}')
    except ImportError: pass
"
grep -r "JWT\|Bearer\|oauth" . --include="*.py" -l 2>/dev/null | grep -v test | head -5
find . -name "test_*.py" | grep integration | head -10
```

Determine:
- [ ] HTTP framework (FastAPI/Flask/Django — each needs different client setup)
- [ ] ORM (Alembic vs Django migrations vs raw SQL)
- [ ] Auth: JWT bearer / session cookies / API keys
- [ ] Whether `create_app()` factory exists — required for test client

---

## Phase 2 — Install Dependencies

```bash
pip install \
  pytest \
  pytest-asyncio \
  pytest-cov \
  httpx \
  "testcontainers[postgres]"
```

---

## Phase 3 — Test Client Setup (conftest.py)

### FastAPI (async)

```python
# tests/conftest.py
import os
import pytest
import pytest_asyncio
from testcontainers.postgres import PostgresContainer
from httpx import AsyncClient, ASGITransport


@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:16-alpine") as pg:
        os.environ["DATABASE_URL"] = pg.get_connection_url()
        _run_migrations(pg.get_connection_url())
        yield pg


def _run_migrations(url: str) -> None:
    import subprocess
    # subprocess.run(["alembic", "upgrade", "head"], env={**os.environ, "DATABASE_URL": url}, check=True)
    print(f"[Setup] Migrations complete")


@pytest_asyncio.fixture(scope="module")
async def client(postgres_container):
    from app.main import create_app  # adjust to your factory
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture(autouse=True)
async def clean_db(postgres_container):
    """Truncate tables between tests."""
    yield
    # Truncate after each test — adapt tables to your schema
    import asyncpg
    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    await conn.execute("TRUNCATE users, items CASCADE")
    await conn.close()
```

### Flask (sync)

```python
# tests/conftest.py
import os
import pytest
from testcontainers.postgres import PostgresContainer


@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:16-alpine") as pg:
        os.environ["DATABASE_URL"] = pg.get_connection_url()
        _run_migrations(pg.get_connection_url())
        yield pg


@pytest.fixture(scope="module")
def client(postgres_container):
    from app import create_app
    app = create_app(testing=True)
    with app.test_client() as c:
        yield c
```

### Django

```python
# tests/conftest.py — use pytest-django
import pytest

@pytest.fixture(scope="session")
def django_db_setup(postgres_container):
    pass  # pytest-django handles DB via DATABASES setting

# In tests, use @pytest.mark.django_db decorator
```

---

## Phase 4 — File Structure

```
tests/
└── integration/
    ├── test_users.py          ← one file per route group
    ├── test_items.py
    ├── test_orders.py
    └── test_auth.py
```

---

## Phase 5 — Write Integration Tests

### Pattern A — Standard REST Endpoint Suite (FastAPI async)

```python
# tests/integration/test_users.py
import pytest
from httpx import AsyncClient
from tests.helpers.auth_helpers import generate_auth_token, generate_expired_token


pytestmark = pytest.mark.integration


class TestCreateUser:
    async def test_201_creates_user_omits_password(self, client: AsyncClient):
        res = await client.post("/api/users", json={
            "email": "alice@example.com",
            "password": "Secure1234!"
        })
        assert res.status_code == 201
        body = res.json()
        assert body["email"] == "alice@example.com"
        assert "id" in body
        assert "password" not in body
        assert "hashed_password" not in body

    async def test_422_rejects_invalid_email(self, client: AsyncClient):
        res = await client.post("/api/users", json={"email": "not-email", "password": "x"})
        assert res.status_code == 422
        errors = res.json().get("detail") or res.json().get("errors", [])
        assert any("email" in str(e).lower() for e in errors)

    async def test_422_rejects_empty_body(self, client: AsyncClient):
        res = await client.post("/api/users", json={})
        assert res.status_code == 422

    async def test_409_rejects_duplicate_email(self, client: AsyncClient):
        payload = {"email": "dup@test.com", "password": "Secure1234!"}
        await client.post("/api/users", json=payload)
        res = await client.post("/api/users", json=payload)
        assert res.status_code == 409


class TestGetUser:
    async def test_200_returns_user_for_valid_id(self, client: AsyncClient):
        # Create user first
        created = await client.post("/api/users", json={"email": "bob@test.com", "password": "x"})
        assert created.status_code == 201
        user_id = created.json()["id"]

        token = generate_auth_token(user_id, role="user")
        res = await client.get(
            f"/api/users/{user_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert res.status_code == 200
        assert res.json()["id"] == user_id

    async def test_401_missing_token(self, client: AsyncClient):
        res = await client.get("/api/users/some-id")
        assert res.status_code == 401

    async def test_403_cross_user_access(self, client: AsyncClient):
        alice = await client.post("/api/users", json={"email": "a@t.com", "password": "x"})
        bob = await client.post("/api/users", json={"email": "b@t.com", "password": "x"})

        alice_token = generate_auth_token(alice.json()["id"], role="user")
        res = await client.get(
            f"/api/users/{bob.json()['id']}",
            headers={"Authorization": f"Bearer {alice_token}"}
        )
        assert res.status_code == 403

    async def test_404_nonexistent_user(self, client: AsyncClient):
        token = generate_auth_token("admin-1", role="admin")
        res = await client.get(
            "/api/users/00000000-0000-0000-0000-000000000000",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert res.status_code == 404


class TestUpdateUser:
    async def test_200_updates_and_returns_user(self, client: AsyncClient):
        created = await client.post("/api/users", json={"email": "carol@test.com", "password": "x"})
        user_id = created.json()["id"]
        token = generate_auth_token(user_id, role="user")

        res = await client.patch(
            f"/api/users/{user_id}",
            json={"display_name": "Carol"},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert res.status_code == 200
        assert res.json()["display_name"] == "Carol"


class TestDeleteUser:
    async def test_204_deletes_user(self, client: AsyncClient):
        created = await client.post("/api/users", json={"email": "del@test.com", "password": "x"})
        user_id = created.json()["id"]
        token = generate_auth_token(user_id, role="admin")

        res = await client.delete(
            f"/api/users/{user_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert res.status_code == 204

        # Verify deletion
        check = await client.get(
            f"/api/users/{user_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert check.status_code == 404
```

### Pattern B — Pagination

```python
# tests/integration/test_items.py
import pytest
from httpx import AsyncClient
from tests.helpers.auth_helpers import generate_auth_token

pytestmark = pytest.mark.integration


class TestListItems:
    async def test_returns_paginated_results(self, client: AsyncClient):
        token = generate_auth_token("admin-1", role="admin")
        headers = {"Authorization": f"Bearer {token}"}

        # Create 15 items
        for i in range(15):
            await client.post("/api/items", json={"name": f"Item {i}"}, headers=headers)

        res = await client.get("/api/items?page=1&limit=10", headers=headers)
        assert res.status_code == 200
        body = res.json()
        assert len(body["items"]) == 10
        assert body["total"] == 15
        assert body["page"] == 1

    async def test_second_page_has_remaining_items(self, client: AsyncClient):
        token = generate_auth_token("admin-1", role="admin")
        headers = {"Authorization": f"Bearer {token}"}

        for i in range(15):
            await client.post("/api/items", json={"name": f"Item {i}"}, headers=headers)

        res = await client.get("/api/items?page=2&limit=10", headers=headers)
        assert res.status_code == 200
        assert len(res.json()["items"]) == 5

    async def test_empty_list_when_no_items(self, client: AsyncClient):
        token = generate_auth_token("u1", role="user")
        res = await client.get("/api/items", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200
        assert res.json()["items"] == []
        assert res.json()["total"] == 0
```

### Pattern C — Flask sync client

```python
# tests/integration/test_users_flask.py
import pytest

pytestmark = pytest.mark.integration


def test_create_user_201(client):
    res = client.post("/api/users", json={"email": "alice@test.com", "password": "Secure123!"})
    assert res.status_code == 201
    assert res.get_json()["email"] == "alice@test.com"


def test_create_user_409_duplicate(client):
    client.post("/api/users", json={"email": "dup@test.com", "password": "x"})
    res = client.post("/api/users", json={"email": "dup@test.com", "password": "y"})
    assert res.status_code == 409
```

---


## Phase 6 — Required HTTP Status Code Coverage

| HTTP Status | When | Required |
|---|---|---|
| 200 / 201 / 204 | Successful operations | ✅ per endpoint |
| 400 | Bad request / invalid body structure | ✅ |
| 401 | Missing or invalid auth token | ✅ per protected endpoint |
| 403 | Valid token but insufficient role | ✅ per role-restricted endpoint |
| 404 | Resource not found by ID | ✅ per GET/PATCH/DELETE by ID |
| 409 | Duplicate / unique constraint | ✅ per unique field endpoint |
| 422 | Validation failure (invalid field values) | ✅ per field with validation |

---

## Phase 7 — Verification Gates

### GATE 1 — Test file for every route group

```bash
echo "====== GATE 1: Integration Test File Coverage ======"
missing=0
for f in $(find app/routes app/routers app/views -name "*.py" 2>/dev/null \
          | grep -v "__init__\|test" | grep -v __pycache__); do
  module=$(basename "$f" .py)
  found=$(find tests/integration -name "test_${module}.py" 2>/dev/null | wc -l)
  [ "$found" -gt 0 ] && echo "  [OK] test_${module}.py" || { echo "  [MISSING] tests/integration/test_${module}.py"; missing=$((missing+1)); }
done
[ "$missing" -eq 0 ] && echo "  GATE 1: PASS" || echo "  GATE 1: FAIL — $missing files missing"
```

### GATE 2 — HTTP status code coverage

```bash
echo "====== GATE 2: HTTP Status Code Coverage ======"
for code in 200 201 204 400 401 403 404 409 422; do
  count=$(grep -r "status_code == $code\|assert.*$code" tests/integration/ 2>/dev/null | wc -l)
  [ "$count" -ge 1 ] \
    && echo "  [PASS] HTTP $code tested: $count" \
    || echo "  [FAIL] HTTP $code never tested"
done
```

### GATE 3 — Auth scenarios covered

```bash
echo "====== GATE 3: Auth Coverage ======"
auth_401=$(grep -r "status_code == 401" tests/integration/ 2>/dev/null | wc -l)
[ "$auth_401" -ge 1 ] && echo "  [PASS] 401 tested: $auth_401" || echo "  [FAIL] No 401 tests"

auth_403=$(grep -r "status_code == 403" tests/integration/ 2>/dev/null | wc -l)
[ "$auth_403" -ge 1 ] && echo "  [PASS] 403 tested: $auth_403" || echo "  [FAIL] No 403 tests"
```

### GATE 4 — Cleanup between tests

```bash
echo "====== GATE 4: Test Isolation ======"
cleanup=$(grep -r "autouse\|TRUNCATE\|deleteMany\|teardown" tests/ --include="*.py" 2>/dev/null | wc -l)
[ "$cleanup" -ge 1 ] \
  && echo "  [PASS] Cleanup present: $cleanup" \
  || echo "  [FAIL] No cleanup — tests may pollute each other"
```

### GATE 5 — All tests pass with real database

```bash
echo "====== GATE 5: Test Execution ======"
pytest -m integration -p no:xdist -v 2>&1 | tail -5
[ $? -eq 0 ] && echo "  GATE 5: PASS" || echo "  GATE 5: FAIL"
```

### GATE 6 — No hardcoded DB URLs

```bash
echo "====== GATE 6: No Hardcoded DB Config ======"
hardcoded=$(grep -rn "localhost:5432\|localhost:3306" tests/integration/ 2>/dev/null)
[ -z "$hardcoded" ] && echo "  GATE 6: PASS" || echo "  GATE 6: FAIL — use Testcontainers: $hardcoded"
```

---

## Final Summary

```bash
echo ""
echo "============================================================"
echo "  INTEGRATION TESTS — COMPLETION REPORT"
echo "============================================================"
echo "  GATE 1 — Test file for every route:        see above"
echo "  GATE 2 — HTTP status code coverage:        see above"
echo "  GATE 3 — Auth (401/403) covered:           see above"
echo "  GATE 4 — Test isolation (cleanup):         see above"
echo "  GATE 5 — All tests pass (real DB):   see above"
echo "  GATE 6 — No hardcoded DB URLs:             see above"
echo ""
echo "  Complete only when ALL gates show PASS."
echo "============================================================"
```

## What comes next

- **Contract tests** → `contract-tests` skill
- **Security tests** → `security-tests` skill

---

---

## Mandatory: Post-Write Review Gate

After writing tests, **before committing**, run the `test-review` skill:
- External service leak scan (every client in `utils/clients/` mocked in conftest)
- DB safety audit (no production defaults, stable IDs, db_manager restore)
- Duplication scan (no copy-pasted infrastructure across files)
- Mock target verification (patch paths match real source)
- Lint + format + combined suite run

No test changes ship without passing this gate.
