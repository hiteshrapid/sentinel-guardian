---
name: test-setup
description: >
  Bootstrap the complete test infrastructure for a backend application from scratch.
  Run this skill FIRST — before any other test skill. It installs all dependencies
  required by all 6 downstream skills (unit, integration, contract, security, smoke, regression),
  creates every directory and scaffold file, writes the master pytest configuration with all test
  project configurations, adds all pyproject.toml/Makefile scripts, creates shared test helpers
  (auth, DB seeding), and validates the entire setup is wired correctly before a single test is
  written. Trigger when the user says "set up testing", "bootstrap test suite", "configure pytest",
  "test infrastructure setup", "set up testing from scratch", "prepare my backend repo for tests",
  or when they are about to use any test skill for the first time. Never skip this
  skill and jump straight into writing tests — a wrong setup causes cascading errors in every
  test file.
---

# Python Monolith — Test Infrastructure Setup Skill

## Stack Adaptation

Before writing any tests, detect the project'"'"'s stack and load the matching context:

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


You are an expert backend QA engineer. Your mission: bootstrap the complete, production-ready test
infrastructure for a backend application so every downstream test skill (unit, integration, contract,
security, smoke, regression) works correctly out of the box.

**Run this skill exactly once, before writing a single test file.**

---

## Phase 1 — Deep Repo Audit

Run every command. Record the outputs — they determine the exact config decisions below.

```bash
# ── Python version ───────────────────────────────────────────
python3 --version
cat pyproject.toml 2>/dev/null | grep -A2 'requires-python\|python_requires' || true
cat setup.cfg 2>/dev/null | grep 'python_requires' || true

# ── Framework ────────────────────────────────────────────────
python3 -c "
import importlib, sys
frameworks = ['fastapi', 'flask', 'django', 'starlette', 'litestar', 'aiohttp']
for f in frameworks:
    try:
        m = importlib.import_module(f)
        print(f'FRAMEWORK: {f} @ {getattr(m, \"__version__\", \"unknown\")}')
    except ImportError:
        pass
"

# ── ORM / DB client ──────────────────────────────────────────
python3 -c "
import importlib
orms = ['sqlalchemy', 'tortoise', 'peewee', 'django.db', 'databases', 'asyncpg', 'psycopg2', 'alembic']
for o in orms:
    try:
        m = importlib.import_module(o)
        print(f'ORM/DB: {o} @ {getattr(m, \"__version__\", \"unknown\")}')
    except ImportError:
        pass
"

# ── Existing test tooling ─────────────────────────────────────
python3 -c "
import importlib
tools = ['pytest', 'unittest', 'httpx', 'requests', 'testcontainers', 'factory_boy', 'faker']
for t in tools:
    try:
        m = importlib.import_module(t)
        print(f'TEST TOOL: {t} @ {getattr(m, \"__version__\", \"unknown\")}')
    except ImportError:
        pass
"

# ── Project structure ─────────────────────────────────────────
find . -type d | grep -v '__pycache__\|\.git\|\.venv\|venv\|node_modules\|\.egg' | sort | head -40
ls -la

# ── Dependency file ───────────────────────────────────────────
cat pyproject.toml 2>/dev/null | head -60 || cat requirements.txt 2>/dev/null | head -30 || true

# ── Auth mechanism ────────────────────────────────────────────
grep -r "JWT\|Bearer\|PyJWT\|python-jose\|passlib" . --include="*.py" -l 2>/dev/null | grep -v test | head -5

# ── Existing test files ───────────────────────────────────────
find . -name "test_*.py" -o -name "*_test.py" | grep -v __pycache__ | head -20

# ── Existing GitHub Actions workflows ────────────────────────
ls .github/workflows/ 2>/dev/null || echo "No workflows yet"
```

**Fill in this decision record before continuing:**

```
FRAMEWORK:        fastapi (async)
ORM:              beanie (MongoDB ODM on motor async driver)
DATABASE:         mongodb
AUTH:             api-key (X-Server-Auth-Key header, server-to-server)
ASYNC:            [ yes (fastapi/starlette/asyncio) | no (flask/django-sync) ]
PYTHON_VERSION:   [ ___ ]
PKG_MANAGER:      [ pip + pyproject.toml | pip + requirements.txt | poetry | uv ]
EXISTING_TESTS:   [ none | some — tool: ___ ]
APP_FACTORY:      [ create_app() exists | app.py exports app | needs creating ]
```

---

## Phase 2 — Install All Dependencies

Install everything all test skills need in one shot. Never install per-skill.

```bash
# ── Linting + Type Checking (FIRST GATE in CI) ───────────────
pip install \
  ruff \
  mypy

# ── Core pytest stack ─────────────────────────────────────────
pip install \
  pytest \
  pytest-asyncio \
  pytest-cov \
  pytest-xdist \
  pytest-mock \
  anyio[trio]

# ── Integration tests: HTTP client + Testcontainers ──────────
pip install \
  httpx \
  testcontainers \
  "testcontainers[postgres]"

# ── Contract tests: OpenAPI validation ────────────────────────
pip install \
  openapi-spec-validator \
  jsonschema \
  pyyaml

# ── Security: dependency audit ────────────────────────────────
pip install \
  pip-audit \
  safety

# ── Security: runtime middleware (not test-only) ──────────────
# For FastAPI:
pip install \
  slowapi \
  python-jose[cryptography] \
  passlib[bcrypt]

# ── Smoke tests: HTTP client ──────────────────────────────────
pip install \
  httpx \
  tenacity

# ── Test data factories ───────────────────────────────────────
pip install \
  factory-boy \
  faker

# ── Coverage reporting ────────────────────────────────────────
pip install \
  coverage[toml]
```

**Verify installation:**
```bash
python3 -c "
required = ['pytest', 'httpx', 'testcontainers', 'openapi_spec_validator',
            'pip_audit', 'factory_boy', 'faker', 'pytest_asyncio', 'pytest_cov',
            'ruff', 'mypy']
for pkg in required:
    try:
        __import__(pkg.replace('-', '_'))
        print(f'  [OK] {pkg}')
    except ImportError:
        print(f'  [MISSING] {pkg}')
"
```

---

## Phase 2b — Configure Linting + Type Checking

Lint and type-check are the **first gate** in CI. Nothing else runs until these pass.

### Ruff Configuration

```toml
# pyproject.toml — add or merge
[tool.ruff]
target-version = "py311"
line-length = 120

[tool.ruff.lint]
select = [
    "E",    # pycodestyle errors
    "W",    # pycodestyle warnings
    "F",    # pyflakes
    "I",    # isort (import sorting)
    "N",    # pep8-naming
    "UP",   # pyupgrade
    "B",    # flake8-bugbear
    "S",    # flake8-bandit (security)
    "T20",  # flake8-print (no print statements)
    "SIM",  # flake8-simplify
    "RUF",  # ruff-specific rules
]
ignore = [
    "S101",  # Allow assert in tests
    "S106",  # Allow hardcoded passwords in tests
]

[tool.ruff.lint.per-file-ignores]
"tests/**/*.py" = ["S101", "S106", "T20"]  # Allow assert, hardcoded passwords, print in tests
```

### Mypy Configuration

```toml
# pyproject.toml — add or merge
[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
ignore_missing_imports = true
check_untyped_defs = true

[[tool.mypy.overrides]]
module = "tests.*"
ignore_errors = true
```

### Verify Lint + Type Check Locally

```bash
# Lint check (fix mode available with --fix)
ruff check .

# Lint auto-fix
ruff check . --fix

# Format check
ruff format --check .

# Type check
mypy . --ignore-missing-imports

# Both should pass before any test run
```

---

## Phase 3 — Create Directory Structure

```bash
# ── Core test infrastructure ──────────────────────────────────
mkdir -p tests/unit
mkdir -p tests/integration
mkdir -p tests/contract
mkdir -p tests/security
mkdir -p tests/fixtures
mkdir -p tests/helpers

# ── Smoke tests ───────────────────────────────────────────────
mkdir -p smoke

# ── GitHub Actions workflows ──────────────────────────────────
mkdir -p .github/workflows

# ── Scripts ───────────────────────────────────────────────────
mkdir -p scripts

# ── __init__.py files ─────────────────────────────────────────
touch tests/__init__.py tests/unit/__init__.py tests/integration/__init__.py
touch tests/contract/__init__.py tests/security/__init__.py
touch tests/fixtures/__init__.py tests/helpers/__init__.py
touch smoke/__init__.py

echo "Directories created:"
find tests smoke .github/workflows scripts -type d | sort
```

**Full expected directory tree after setup:**
```
project-root/
├── tests/
│   ├── conftest.py              ← shared fixtures (DB, app client)
│   ├── unit/
│   │   └── test_*.py
│   ├── integration/
│   │   └── test_*.py
│   ├── contract/
│   │   ├── openapi-baseline.json
│   │   └── test_openapi_contract.py
│   ├── security/
│   │   └── test_*.py
│   ├── helpers/
│   │   ├── auth_helpers.py     ← JWT token generation for tests
│   │   └── db_helpers.py       ← seed/truncate utilities
│   └── fixtures/
│       └── factories.py        ← factory_boy model factories
├── smoke/
│   ├── conftest.py
│   └── test_smoke.py
├── scripts/
│   └── generate_openapi_baseline.py
├── pyproject.toml              ← pytest + coverage config
├── .coveragerc                 ← coverage config (if not in pyproject.toml)
├── audit-policy.json           ← pip-audit policy
└── .github/
    └── workflows/
        ├── ci.yml
        ├── deploy.yml
        └── regression.yml
```

---

## Phase 4 — Write pytest Configuration

```toml
# pyproject.toml — add or merge this [tool.pytest.ini_options] section
[tool.pytest.ini_options]
asyncio_mode = "auto"        # pytest-asyncio: auto-detect async tests
testpaths = ["tests"]
python_files = ["test_*.py", "*_test.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]

# Markers for filtering test types
markers = [
    "unit: fast unit tests with no I/O",
    "integration: tests requiring real DB (Testcontainers)",
    "contract: OpenAPI schema validation tests",
    "security: security and auth boundary tests",
    "smoke: post-deploy health checks",
    "regression: tests added to prevent specific bug regressions",
]

addopts = [
    "--strict-markers",       # fail on unknown markers
    "-ra",                    # show summary of non-passing tests
    "--tb=short",             # shorter tracebacks
]

[tool.coverage.run]
source = ["app", "src"]       # adjust to your source directory
omit = [
    "*/tests/*",
    "*/migrations/*",
    "*/alembic/*",
    "*/__init__.py",
    "*/config.py",
    "*/main.py",
]
branch = true

[tool.coverage.report]
fail_under = 80
show_missing = true
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise NotImplementedError",
    "if TYPE_CHECKING:",
    "pass",
]
```

**Makefile targets** (create or append):
```makefile
# Makefile
.PHONY: lint type-check test-unit test-integration test-contract test-security test-resilience test-smoke test-e2e test-all

# ── Linting + Type Checking (FIRST GATE) ─────────────────────
lint:
	ruff check .
	ruff format --check .

lint-fix:
	ruff check . --fix
	ruff format .

type-check:
	mypy . --ignore-missing-imports

# ── Test Suites ──────────────────────────────────────────────
test-unit:
	pytest tests/unit/ --cov --cov-report=term-missing --cov-fail-under=100

test-unit-watch:
	pytest-watch -- tests/unit/

test-integration:
	pytest tests/integration/ -p no:xdist -v

test-contract:
	pytest tests/contract/ -v

test-security:
	pytest tests/security/ -v

test-resilience:
	pytest tests/resilience/ -v

test-smoke:
	SMOKE_BASE_URL=http://localhost:8000 pytest smoke/ --timeout=60 -v

test-smoke-deployed:
	pytest smoke/ --timeout=60 -v

test-e2e:
	pytest tests/e2e/ --timeout=120 -v

test-all:
	pytest --cov --cov-report=html --cov-fail-under=100

# ── CI Pipeline Order (matches ci.yml) ───────────────────────
test-ci: lint type-check test-unit test-integration test-contract test-security

# ── Security Audit ───────────────────────────────────────────
security-audit:
	pip-audit --desc

security-outdated:
	pip list --outdated
```

---

## Phase 5 — Write Shared Infrastructure Files

### 5a — Root conftest.py (Testcontainers + App Client)

```python
# tests/conftest.py
import asyncio
import os
import pytest
import pytest_asyncio
from testcontainers.postgres import PostgresContainer

# ── Testcontainers: start once for the entire session ─────────
@pytest.fixture(scope="session")
def mongo_container():
    """Start a real MongoDB container for the test session."""
    from testcontainers.mongodb import MongoDbContainer
    with MongoDbContainer("mongo:7") as mongo:
        os.environ["MONGODB_URI"] = mongo.get_connection_url()
        os.environ["MONGODB_DATABASE"] = "test_db"
        yield mongo


def _run_migrations(database_url: str) -> None:
    """Run DB migrations against the test container."""
    import subprocess
    # ── Alembic ────────────────────────────────────────────
    # subprocess.run(
    #     ["alembic", "upgrade", "head"],
    #     env={**os.environ, "DATABASE_URL": database_url},
    #     check=True,
    # )
    # ── Django ─────────────────────────────────────────────
    # subprocess.run(["python", "manage.py", "migrate"], check=True)
    # ── Raw SQL ────────────────────────────────────────────
    # subprocess.run(["psql", database_url, "-f", "schema.sql"], check=True)
    print(f"[Test Setup] Migrations complete for {database_url}")


# ── FastAPI / Starlette app client ────────────────────────────
@pytest_asyncio.fixture(scope="module")
async def client(postgres_container):
    """Async HTTP test client backed by a real Postgres container."""
    from httpx import AsyncClient, ASGITransport
    # Adjust import to match your app factory
    # from app.main import create_app
    # app = create_app()
    # async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
    #     yield c
    raise NotImplementedError("Update this fixture with your app factory import")


# ── Sync client (Flask / Django) ──────────────────────────────
# @pytest.fixture(scope="module")
# def client(postgres_container):
#     from app import create_app
#     app = create_app(testing=True)
#     with app.test_client() as c:
#         yield c
```

### 5b — Auth Helpers

```python
# tests/helpers/auth_helpers.py
"""JWT token generation helpers for use in integration and security tests."""
from datetime import datetime, timedelta, timezone
from typing import Literal

try:
    from jose import jwt
    _BACKEND = "jose"
except ImportError:
    try:
        import jwt as _pyjwt
        _BACKEND = "pyjwt"
    except ImportError:
        raise ImportError("Install python-jose[cryptography] or PyJWT")

TEST_SERVER_AUTH_KEY = "test-server-auth-key-for-testing-only"
TEST_JWT_ALGORITHM = "HS256"


def generate_auth_token(
    user_id: str,
    role: Literal["user", "admin", "moderator"] = "user",
    email: str | None = None,
    expires_delta: timedelta = timedelta(hours=1),
) -> str:
    """Generate a valid JWT for use in test requests."""
    payload = {
        "sub": user_id,
        "userId": user_id,
        "email": email or f"{user_id}@test.com",
        "role": role,
        "exp": datetime.now(timezone.utc) + expires_delta,
        "iat": datetime.now(timezone.utc),
    }
    if _BACKEND == "jose":
        return jwt.encode(payload, TEST_JWT_SECRET, algorithm=TEST_JWT_ALGORITHM)
    else:
        return _pyjwt.encode(payload, TEST_JWT_SECRET, algorithm=TEST_JWT_ALGORITHM)


def generate_expired_token(user_id: str) -> str:
    """Generate an already-expired JWT — use to test 401 on expired tokens."""
    return generate_auth_token(user_id, expires_delta=timedelta(seconds=-1))


def generate_tampered_token(user_id: str) -> str:
    """Generate a token signed with wrong secret — use to test 401 on tampered tokens."""
    payload = {
        "sub": user_id,
        "userId": user_id,
        "role": "user",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    if _BACKEND == "jose":
        return jwt.encode(payload, "wrong-secret-key", algorithm=TEST_JWT_ALGORITHM)
    else:
        return _pyjwt.encode(payload, "wrong-secret-key", algorithm=TEST_JWT_ALGORITHM)


# Pre-built tokens for common test scenarios
class TestTokens:
    user = generate_auth_token("test-user-001", role="user", email="user@test.com")
    admin = generate_auth_token("test-admin-001", role="admin", email="admin@test.com")
    expired = generate_expired_token("test-user-001")
    tampered = generate_tampered_token("test-user-001")


test_tokens = TestTokens()
```

### 5c — DB Helpers

```python
# tests/helpers/db_helpers.py
"""Database seed/truncate utilities for integration tests."""
import asyncio
from typing import Any


async def truncate_tables(tables: list[str], db=None) -> None:
    """Truncate tables between tests to ensure isolation.

    Usage:
        @pytest.fixture(autouse=True)
        async def clean_db(db_session):
            yield
            await truncate_tables(["users", "orders"], db_session)
    """
    # SQLAlchemy async:
    # async with db.begin():
    #     for table in tables:
    #         await db.execute(text(f'TRUNCATE TABLE "{table}" CASCADE'))

    # Tortoise ORM:
    # from tortoise import Tortoise
    # conn = Tortoise.get_connection("default")
    # for table in tables:
    #     await conn.execute_query(f'TRUNCATE TABLE "{table}" CASCADE')

    print(f"[DB Helpers] truncate_tables called for: {tables}")


async def seed_user(
    db=None,
    email: str | None = None,
    role: str = "user",
    password: str = "hashed_test_password",
) -> dict[str, Any]:
    """Seed a user directly into the DB — bypasses the API layer for test setup."""
    import time
    email = email or f"seed-{int(time.time() * 1000)}@test.com"

    # SQLAlchemy async example:
    # result = await db.execute(
    #     insert(User).values(email=email, hashed_password=password, role=role)
    #     .returning(User.id, User.email)
    # )
    # return result.fetchone()._asdict()

    return {"id": f"seed-user-{int(time.time() * 1000)}", "email": email}


async def clean_database(db=None) -> None:
    """Truncate all test data. Call in teardown if truncate_tables is too granular."""
    # await db.execute(text("TRUNCATE users, orders, items CASCADE"))
    print("[DB Helpers] clean_database called")
```

### 5d — Factory Boy Fixtures

```python
# tests/fixtures/factories.py
"""Factory-boy model factories for generating consistent test data."""
import factory
from faker import Faker

fake = Faker()


class UserFactory(factory.Factory):
    """Factory for generating User test data."""
    class Meta:
        # Replace with your actual User model
        # model = User
        model = dict  # placeholder — replace with your model

    id = factory.LazyFunction(lambda: str(fake.uuid4()))
    email = factory.LazyFunction(fake.email)
    password = "TestPassword123!"
    role = "user"
    created_at = factory.LazyFunction(fake.date_time)


class ItemFactory(factory.Factory):
    """Factory for generating Item test data."""
    class Meta:
        model = dict  # placeholder

    id = factory.LazyFunction(lambda: str(fake.uuid4()))
    name = factory.LazyFunction(lambda: f"Test Item {fake.word()}")
    description = factory.LazyFunction(fake.sentence)
    price = factory.LazyFunction(lambda: round(fake.pyfloat(min_value=1, max_value=999), 2))


# Usage:
# user_data = UserFactory()             → dict with fake data
# user_data = UserFactory(role="admin") → override specific fields
```

### 5e — pip-audit Policy File

```json
// audit-policy.json
{
  "ignore_vulns": [],
  "format": "json"
}
```

### 5f — OpenAPI Baseline Script

```python
# scripts/generate_openapi_baseline.py
"""
Generates the OpenAPI baseline JSON file used by contract tests.
Run once after setup, then commit the output.

Usage: python scripts/generate_openapi_baseline.py
"""
import asyncio
import json
import os
import sys
from pathlib import Path


async def generate() -> None:
    # FastAPI example:
    # from app.main import create_app
    # import httpx
    # app = create_app()
    # async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
    #     res = await client.get("/openapi.json")
    #     assert res.status_code == 200, f"Failed to fetch schema: {res.status_code}"
    #     schema = res.json()

    # Django / Flask: fetch from running server or generate directly
    # schema = app.openapi()

    out_path = Path("tests/contract/openapi-baseline.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # out_path.write_text(json.dumps(schema, indent=2))
    print(f"Baseline written to: {out_path}")
    print("Commit this file: git add tests/contract/openapi-baseline.json")


if __name__ == "__main__":
    asyncio.run(generate())
```

---

## Phase 6 — Write GitHub Actions Workflow Stubs

### ci.yml

Pipeline order matches the canonical CI pipeline:
1. **lint-typecheck** — first gate, blocks everything
2. **unit** + **security-tests** + **integration** — parallel, all need lint
3. **contract** — needs unit + integration
4. **security-audit** — independent, runs in parallel

```yaml
# .github/workflows/ci.yml
name: CI

on:
  pull_request:
  push:
    branches: [main, dev, qa]

jobs:
  lint-typecheck:
    name: Lint + Type Check
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install ruff mypy
      - run: ruff check .
      - run: ruff format --check .
      - run: mypy . --ignore-missing-imports

  unit:
    name: Unit Tests
    runs-on: ubuntu-latest
    needs: lint-typecheck
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -e ".[dev]"  # or: pip install -r requirements.txt --extra dev
      - run: make test-unit
      - name: Upload coverage
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: coverage-report
          path: htmlcov/

  integration:
    name: Integration Tests
    runs-on: ubuntu-latest
    needs: lint-typecheck
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -e ".[dev]"
      - name: Run integration tests
        run: make test-integration
        env:
          TESTCONTAINERS_RYUK_DISABLED: true

  security-tests:
    name: Security Tests
    runs-on: ubuntu-latest
    needs: lint-typecheck
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -e ".[dev]"
      - run: make test-security

  contract:
    name: Contract Tests
    runs-on: ubuntu-latest
    needs: [unit, integration]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -e ".[dev]"
      - run: make test-contract

  security-audit:
    name: Security Audit
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install pip-audit
      - run: make security-audit
```

### deploy.yml

Post-deploy order: **deploy → smoke → e2e** (e2e only runs if smoke passes).

```yaml
# .github/workflows/deploy.yml
name: Deploy + Smoke + E2E

on:
  push:
    branches: [main, dev, qa]

jobs:
  deploy:
    name: Deploy
    runs-on: ubuntu-latest
    outputs:
      deploy_url: ${{ steps.set-url.outputs.url }}
    steps:
      - uses: actions/checkout@v4
      # ── Replace with your actual deploy command ──────────
      # Uses reusable workflows: ruh-ai/reusable-workflows-and-charts
      - name: Deploy
        run: echo "Add your deploy command here"
      - name: Set deploy URL
        id: set-url
        run: echo "url=${{ vars.DEV_URL }}" >> $GITHUB_OUTPUT

  smoke:
    name: Smoke Tests
    runs-on: ubuntu-latest
    needs: deploy
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install httpx pytest tenacity
      - name: Wait for service ready
        run: |
          URL="${{ needs.deploy.outputs.deploy_url }}/health"
          for i in $(seq 1 24); do
            STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$URL" || echo "000")
            echo "Attempt $i: $STATUS"
            [ "$STATUS" = "200" ] && echo "Ready" && exit 0
            sleep 5
          done
          echo "Service not ready after 2 minutes" && exit 1
      - name: Run smoke tests
        run: make test-smoke-deployed
        timeout-minutes: 2
        env:
          SMOKE_BASE_URL: ${{ needs.deploy.outputs.deploy_url }}
          SMOKE_AUTH_TOKEN: ${{ secrets.SMOKE_AUTH_TOKEN }}
      - name: Rollback on smoke failure
        if: failure()
        run: echo "Add your rollback command here"

  e2e:
    name: E2E Tests
    runs-on: ubuntu-latest
    needs: smoke
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -e ".[dev]" playwright && playwright install chromium
      - name: Run E2E tests
        run: make test-e2e
        timeout-minutes: 10
        env:
          E2E_BASE_URL: ${{ needs.deploy.outputs.deploy_url }}
          E2E_API_KEY: ${{ secrets.DEV_API_KEY }}
```

### regression.yml

Nightly runs ALL layers as separate jobs. Slack alert on any failure.

```yaml
# .github/workflows/regression.yml
name: Nightly Regression

on:
  schedule:
    - cron: '0 2 * * *'
  workflow_dispatch:

jobs:
  regression-unit:
    name: Unit Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -e ".[dev]"
      - run: make test-unit

  regression-integration:
    name: Integration Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -e ".[dev]"
      - run: make test-integration
        env:
          TESTCONTAINERS_RYUK_DISABLED: true

  regression-contract:
    name: Contract Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -e ".[dev]"
      - run: make test-contract
      - run: make test-contract

  regression-security:
    name: Security Audit + Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -e ".[dev]" pip-audit
      - run: make security-audit
      - run: make test-security

  regression-smoke:
    name: Smoke Tests (Deployed)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install httpx pytest tenacity
      - run: make test-smoke-deployed
        env:
          SMOKE_BASE_URL: ${{ vars.DEV_URL }}
          SMOKE_AUTH_TOKEN: ${{ secrets.DEV_API_KEY }}

  regression-e2e:
    name: E2E Tests (Deployed)
    runs-on: ubuntu-latest
    needs: regression-smoke
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -e ".[dev]" playwright && playwright install chromium
      - run: make test-e2e
        timeout-minutes: 10
        env:
          E2E_BASE_URL: ${{ vars.DEV_URL }}
          E2E_API_KEY: ${{ secrets.DEV_API_KEY }}

  notify-on-failure:
    name: Slack Alert
    runs-on: ubuntu-latest
    needs: [regression-unit, regression-integration, regression-contract, regression-security, regression-smoke, regression-e2e]
    if: failure()
    steps:
      - uses: slackapi/slack-github-action@v1
        with:
          channel-id: ${{ secrets.SLACK_ALERTS_CHANNEL }}
          slack-message: |
            ❌ *Nightly Regression Failed* — ${{ github.repository }}
            Run: ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}
        env:
          SLACK_BOT_TOKEN: ${{ secrets.SLACK_BOT_TOKEN }}
```

---

## Phase 7 — Verify the Entire Setup

### CHECK 1 — Directory structure

```bash
echo "====== CHECK 1: Directory Structure ======"
required_dirs=(
  "tests" "tests/unit" "tests/integration" "tests/contract"
  "tests/security" "tests/fixtures" "tests/helpers"
  "smoke" "scripts" ".github/workflows"
)
all_ok=true
for d in "${required_dirs[@]}"; do
  [ -d "$d" ] && echo "  [OK] $d" || { echo "  [MISSING] $d"; all_ok=false; }
done
$all_ok && echo "  CHECK 1: PASS" || echo "  CHECK 1: FAIL"
```

### CHECK 2 — Required files exist

```bash
echo "====== CHECK 2: Required Files ======"
required_files=(
  "tests/conftest.py"
  "tests/helpers/auth_helpers.py"
  "tests/helpers/db_helpers.py"
  "tests/fixtures/factories.py"
  "scripts/generate_openapi_baseline.py"
  ".github/workflows/ci.yml"
  ".github/workflows/deploy.yml"
  ".github/workflows/regression.yml"
)
all_ok=true
for f in "${required_files[@]}"; do
  [ -f "$f" ] && echo "  [OK] $f" || { echo "  [MISSING] $f"; all_ok=false; }
done
$all_ok && echo "  CHECK 2: PASS" || echo "  CHECK 2: FAIL"
```

### CHECK 3 — All dependencies installed

```bash
echo "====== CHECK 3: Dependencies ======"
python3 -c "
required = ['pytest','httpx','testcontainers','openapi_spec_validator',
            'pip_audit','factory_boy','faker','pytest_asyncio','pytest_cov']
missing = []
for pkg in required:
    try: __import__(pkg.replace('-','_'))
    except ImportError: missing.append(pkg)
if missing:
    print('  [MISSING]:', ', '.join(missing))
    exit(1)
else:
    print('  CHECK 3: PASS')
"
```

### CHECK 4 — pytest config valid

```bash
echo "====== CHECK 4: Pytest Config Validation ======"
pytest --co -q 2>&1 | head -10
[ $? -eq 0 ] && echo "  CHECK 4: PASS" || echo "  CHECK 4: FAIL"
```

### CHECK 5 — Testcontainers can start Postgres

```bash
echo "====== CHECK 5: Testcontainers Smoke ======"
python3 -c "
from testcontainers.postgres import PostgresContainer
print('  Starting container...')
with PostgresContainer('postgres:16-alpine') as pg:
    url = pg.get_connection_url()
    print(f'  [OK] Container started (URL hidden)')
    print('  CHECK 5: PASS')
" 2>&1
```

### CHECK 6 — Workflow YAML valid

```bash
echo "====== CHECK 6: Workflow YAML Validity ======"
python3 -c "
import yaml, pathlib
for f in pathlib.Path('.github/workflows').glob('*.yml'):
    try:
        yaml.safe_load(f.read_text())
        print(f'  [OK] {f}')
    except yaml.YAMLError as e:
        print(f'  [INVALID YAML] {f}: {e}')
"
```

---

## Phase 8 — Final Summary

```bash
echo ""
echo "================================================================"
echo "  PY MONOLITH TEST INFRASTRUCTURE — SETUP COMPLETION REPORT"
echo "================================================================"
echo "  CHECK 1 — Directory structure:        see above"
echo "  CHECK 2 — Required files created:     see above"
echo "  CHECK 3 — All dependencies installed: see above"
echo "  CHECK 4 — Pytest config valid:        see above"
echo "  CHECK 5 — Testcontainers works:       see above"
echo "  CHECK 6 — Workflow YAML valid:        see above"
echo ""
echo "  All 6 checks PASS? You are ready to use the test skills."
echo ""
echo "  Recommended skill order:"
echo "  1. unit-tests"
echo "  2. integration-tests"
echo "  3. contract-tests"
echo "  4. security-tests"
echo "  5. smoke-tests"
echo "  6. regression-tests"
echo "================================================================"
```

---

## Adaptation Guide by Framework

### FastAPI
- Use `httpx.AsyncClient` with `ASGITransport` in conftest.py
- OpenAPI schema at `/openapi.json` by default
- Use `pytest-asyncio` with `asyncio_mode = "auto"`

### Flask
- Use `app.test_client()` in conftest.py (sync)
- Use `flask-openapi3` or `flasgger` for OpenAPI schema
- `pytest-asyncio` not needed unless using async views

### Django
- Use `django.test.AsyncClient` or DRF's `APIClient`
- `pytest-django` provides fixtures and `@pytest.mark.django_db`
- OpenAPI via `drf-spectacular` at `/api/schema/`

### SQLAlchemy Async
In `_run_migrations`:
```python
from alembic.config import Config
from alembic import command
alembic_cfg = Config("alembic.ini")
alembic_cfg.set_main_option("sqlalchemy.url", database_url)
command.upgrade(alembic_cfg, "head")
```
