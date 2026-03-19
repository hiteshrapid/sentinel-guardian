---
name: smoke-tests
description: >
  Implement post-deploy smoke tests for a backend application and set up the GitHub Actions
  deploy workflow that triggers them automatically after every deployment. Use this skill when the
  user wants to verify a deployment is alive, set up a deploy.yml workflow, add health check tests,
  verify DB connectivity post-deploy, or build a rollback trigger from smoke test failures. Trigger
  when the user mentions "smoke tests Python", "post-deploy tests Python", "health check after
  deploy Python", "deploy.yml GitHub Actions Python", "verify deployment Python", "canary deploy
  checks Python", or "automatic rollback on deploy failure Python". Always use this skill when
  setting up the deployment pipeline for a backend application — smoke tests are the first line of
  defense after every deploy.
---

# Python Monolith — Smoke Tests Skill

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


You are an expert backend QA engineer. Your mission: implement post-deploy smoke tests for a
backend application that verify the deployed service is alive, reachable, and minimally functional
within 60 seconds of deploy.

**Smoke tests answer: "Is the deployed service healthy enough to receive real traffic?"**
They do NOT test business logic — that is unit/integration territory.
They test: health endpoint, DB connectivity, auth round-trip, 1-2 critical read paths.

---

## Phase 1 — Audit the Repo

```bash
# Is there a health endpoint?
grep -r "health\|ping\|status" . --include="*.py" -l 2>/dev/null | grep -v test | head -5
grep -r "@.*route.*health\|@.*get.*health" . --include="*.py" 2>/dev/null | head -5

# Is there a deploy workflow?
ls .github/workflows/ 2>/dev/null
cat .github/workflows/deploy.yml 2>/dev/null | head -30

# Auth mechanism
grep -r "JWT\|Bearer\|api.key\|API_KEY" . --include="*.py" -l 2>/dev/null | grep -v test | head -5
```

Determine:
- [ ] Health endpoint exists? (`/health`, `/ping`, `/status`)
- [ ] Does health check DB connectivity?
- [ ] Auth type for critical read paths (JWT / API key / none)
- [ ] Deployment target (Fly.io, Railway, Kubernetes, EC2)

---

## Phase 2 — Install Dependencies

```bash
pip install \
  httpx \
  pytest \
  pytest-asyncio \
  tenacity     # retry logic for waiting on service ready
```

---

## Phase 3 — Create the Health Endpoint (if missing)

The health endpoint is the foundation of smoke tests. It must exist before anything else.

### FastAPI

```python
# app/routers/health.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
# from app.database import get_db

router = APIRouter()


@router.get("/health")
async def health_check():
    """Basic liveness check — returns 200 if the process is running."""
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness_check():
    """Readiness check — verifies DB connectivity. Returns 503 if DB is down."""
    try:
        # Adapt to your DB client
        # async with get_db() as db:
        #     await db.execute(text("SELECT 1"))
        return {"status": "ready", "db": "ok"}
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail=f"DB not ready: {str(e)}")
```

### Flask

```python
# app/routes/health.py
from flask import Blueprint, jsonify

health_bp = Blueprint("health", __name__)


@health_bp.get("/health")
def health_check():
    return jsonify({"status": "ok"}), 200


@health_bp.get("/health/ready")
def readiness_check():
    try:
        # from app.extensions import db
        # db.session.execute(text("SELECT 1"))
        return jsonify({"status": "ready", "db": "ok"}), 200
    except Exception as e:
        return jsonify({"status": "error", "detail": str(e)}), 503
```

---

## Phase 4 — Write Smoke Tests

```python
# smoke/test_smoke.py
"""
Post-deploy smoke tests.
Run against a live deployed environment, not against a test container.

Usage:
    SMOKE_BASE_URL=https://staging.example.com pytest smoke/ -v
    SMOKE_BASE_URL=http://localhost:8000 pytest smoke/ -v  # local verification
"""
import os
import pytest
import httpx
from tenacity import retry, stop_after_delay, wait_fixed

BASE_URL = os.environ.get("SMOKE_BASE_URL", "http://localhost:8000").rstrip("/")
AUTH_TOKEN = os.environ.get("SMOKE_AUTH_TOKEN", "")

# Shared client for all smoke tests
@pytest.fixture(scope="module")
def client():
    with httpx.Client(base_url=BASE_URL, timeout=30) as c:
        yield c


@pytest.fixture(scope="module")
def auth_headers():
    if AUTH_TOKEN:
        return {"Authorization": f"Bearer {AUTH_TOKEN}"}
    return {}


# ── Liveness ───────────────────────────────────────────────────────────────


@pytest.mark.smoke
def test_health_returns_200(client: httpx.Client):
    """Service must be alive and responding."""
    res = client.get("/health")
    assert res.status_code == 200, f"Health check failed: {res.status_code} — {res.text}"


@pytest.mark.smoke
def test_health_returns_ok_status(client: httpx.Client):
    """Health response must contain a status field."""
    res = client.get("/health")
    body = res.json()
    assert body.get("status") in ("ok", "healthy", "up"), f"Unexpected status: {body}"


# ── Readiness ──────────────────────────────────────────────────────────────


@pytest.mark.smoke
def test_readiness_check_db_connectivity(client: httpx.Client):
    """DB must be reachable from the deployed service."""
    res = client.get("/health/ready")
    assert res.status_code == 200, (
        f"Readiness check failed (DB may be down): {res.status_code} — {res.text}"
    )
    body = res.json()
    assert body.get("db") in ("ok", "connected", "healthy"), f"DB not ready: {body}"


# ── Auth ───────────────────────────────────────────────────────────────────


@pytest.mark.smoke
def test_protected_endpoint_requires_auth(client: httpx.Client):
    """Protected endpoints must reject unauthenticated requests."""
    res = client.get("/api/users/me")
    assert res.status_code == 401, (
        f"Expected 401 for unauthenticated request, got: {res.status_code}"
    )


@pytest.mark.smoke
def test_authenticated_request_succeeds(client: httpx.Client, auth_headers: dict):
    """Authenticated request to a read-only endpoint must return 200."""
    if not auth_headers:
        pytest.skip("SMOKE_AUTH_TOKEN not set — skipping auth smoke test")

    res = client.get("/api/users/me", headers=auth_headers)
    assert res.status_code == 200, (
        f"Authenticated request failed: {res.status_code} — {res.text}"
    )


# ── Critical Read Paths ────────────────────────────────────────────────────


@pytest.mark.smoke
def test_api_root_responds(client: httpx.Client):
    """API root must respond — proves routing is working."""
    res = client.get("/api")
    assert res.status_code in (200, 404), (
        f"API root returned unexpected status: {res.status_code}"
    )
    # 404 is acceptable if there's no index route — 500 is not


@pytest.mark.smoke
def test_openapi_schema_accessible(client: httpx.Client):
    """OpenAPI schema endpoint must be reachable — proves app boot was clean."""
    res = client.get("/openapi.json")
    if res.status_code == 404:
        pytest.skip("No OpenAPI endpoint found — skipping")
    assert res.status_code == 200
    assert res.headers.get("content-type", "").startswith("application/json")


# ── Response Time ──────────────────────────────────────────────────────────


@pytest.mark.smoke
def test_health_responds_within_timeout(client: httpx.Client):
    """Health check must respond within 5 seconds."""
    import time
    start = time.time()
    res = client.get("/health")
    elapsed = time.time() - start
    assert res.status_code == 200
    assert elapsed < 5.0, f"Health check too slow: {elapsed:.2f}s"
```

---

## Phase 5 — Async Smoke Tests (FastAPI with httpx async)

```python
# smoke/test_smoke_async.py
import os
import pytest
import httpx

BASE_URL = os.environ.get("SMOKE_BASE_URL", "http://localhost:8000").rstrip("/")
AUTH_TOKEN = os.environ.get("SMOKE_AUTH_TOKEN", "")

pytestmark = [pytest.mark.smoke, pytest.mark.asyncio]


@pytest.fixture(scope="module")
async def async_client():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as c:
        yield c


async def test_health_async(async_client: httpx.AsyncClient):
    res = await async_client.get("/health")
    assert res.status_code == 200


async def test_readiness_async(async_client: httpx.AsyncClient):
    res = await async_client.get("/health/ready")
    assert res.status_code == 200
```

---

## Phase 6 — Smoke Test conftest.py

```python
# smoke/conftest.py
import os
import pytest
import httpx
from tenacity import retry, stop_after_delay, wait_fixed, retry_if_exception_type

BASE_URL = os.environ.get("SMOKE_BASE_URL", "http://localhost:8000").rstrip("/")


def pytest_configure(config):
    config.addinivalue_line("markers", "smoke: post-deploy health checks")


@pytest.fixture(scope="session", autouse=True)
def wait_for_service():
    """Wait up to 120 seconds for the service to be ready before running smoke tests."""
    @retry(
        stop=stop_after_delay(120),
        wait=wait_fixed(5),
        retry=retry_if_exception_type((httpx.ConnectError, httpx.RemoteProtocolError)),
        reraise=True,
    )
    def _wait():
        with httpx.Client(timeout=10) as c:
            res = c.get(f"{BASE_URL}/health")
            assert res.status_code == 200, f"Health check returned {res.status_code}"
            print(f"  Service ready at {BASE_URL}")

    print(f"\n  Waiting for service at {BASE_URL}...")
    _wait()
```

---

## Phase 7 — pytest config for smoke tests

```toml
# pyproject.toml — add smoke test config
[tool.pytest.ini_options]
# ... existing config ...

# Smoke tests use a separate config invocation:
# pytest smoke/ --timeout=60
```

Or add a `smoke/pytest.ini`:
```ini
[pytest]
asyncio_mode = auto
timeout = 60
markers =
    smoke: post-deploy health checks
```

**Makefile:**
```makefile
test-smoke:
	pytest smoke/ -v --timeout=60

test-smoke-local:
	SMOKE_BASE_URL=http://localhost:8000 pytest smoke/ -v --timeout=60
```

---

## Phase 8 — deploy.yml with Smoke Gate

```yaml
# .github/workflows/deploy.yml
name: Deploy + Smoke

on:
  push:
    branches: [main]

jobs:
  deploy:
    name: Deploy to Staging
    runs-on: ubuntu-latest
    outputs:
      deploy_url: ${{ steps.set-url.outputs.url }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install -r requirements.txt

      # ── Replace with your deploy command ─────────────────
      # - run: fly deploy --remote-only
      # - run: railway up
      # - run: kubectl set image deployment/api api=$IMAGE

      - name: Deploy
        run: echo "Add your deploy command here"

      - name: Set staging URL
        id: set-url
        run: echo "url=${{ secrets.STAGING_URL }}" >> $GITHUB_OUTPUT

  smoke:
    name: Smoke Tests
    runs-on: ubuntu-latest
    needs: deploy
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install httpx pytest pytest-asyncio tenacity

      - name: Run smoke tests
        run: pytest smoke/ -v --timeout=60
        timeout-minutes: 2
        env:
          SMOKE_BASE_URL: ${{ needs.deploy.outputs.deploy_url }}
          SMOKE_AUTH_TOKEN: ${{ secrets.SMOKE_AUTH_TOKEN }}

      - name: Rollback on smoke failure
        if: failure()
        run: |
          echo "Smoke tests failed — rolling back"
          # fly releases | head -3 && fly deploy --image <prev>
          # railway rollback
          echo "Add your rollback command here"
```

---

## Phase 9 — Verification Gates

### GATE 1 — Health endpoint exists

```bash
echo "====== GATE 1: Health Endpoint ======"
health=$(grep -r "@.*get.*['\"].*health\|route.*health" . --include="*.py" 2>/dev/null | grep -v test | wc -l)
[ "$health" -ge 1 ] \
  && echo "  GATE 1: PASS — Health endpoint found" \
  || echo "  GATE 1: FAIL — Create GET /health endpoint"
```

### GATE 2 — Smoke test files exist

```bash
echo "====== GATE 2: Smoke Test Files ======"
smoke_tests=$(find smoke/ -name "test_*.py" 2>/dev/null | wc -l)
[ "$smoke_tests" -ge 1 ] \
  && echo "  GATE 2: PASS — $smoke_tests smoke test files" \
  || echo "  GATE 2: FAIL — No smoke tests in smoke/"
```

### GATE 3 — Required scenarios covered

```bash
echo "====== GATE 3: Required Smoke Scenarios ======"
for scenario in "status_code == 200" "401\|requires_auth" "db\|ready" "timeout\|elapsed"; do
  count=$(grep -r "$scenario" smoke/ --include="*.py" 2>/dev/null -i | wc -l)
  [ "$count" -ge 1 ] \
    && echo "  [PASS] '$scenario' covered" \
    || echo "  [WARN] Consider adding test for: $scenario"
done
```

### GATE 4 — Deploy workflow has smoke gate

```bash
echo "====== GATE 4: Deploy Workflow ======"
[ -f ".github/workflows/deploy.yml" ] \
  && echo "  [PASS] deploy.yml exists" \
  || echo "  [FAIL] Missing deploy.yml"

grep -q "smoke\|SMOKE_BASE_URL" .github/workflows/deploy.yml 2>/dev/null \
  && echo "  [PASS] Smoke gate in deploy.yml" \
  || echo "  [FAIL] No smoke gate in deploy.yml"

grep -q "rollback\|Rollback" .github/workflows/deploy.yml 2>/dev/null \
  && echo "  [PASS] Rollback step present" \
  || echo "  [WARN] No rollback step — add one"
```

### GATE 5 — Smoke tests pass locally

```bash
echo "====== GATE 5: Local Smoke Test Execution ======"
# Start your app in background first, then:
SMOKE_BASE_URL=http://localhost:8000 pytest smoke/ -v --timeout=60 2>&1 | tail -5
[ $? -eq 0 ] && echo "  GATE 5: PASS" || echo "  GATE 5: FAIL"
```

---

## Final Summary

```bash
echo ""
echo "============================================================"
echo "  PY MONOLITH SMOKE TESTS — COMPLETION REPORT"
echo "============================================================"
echo "  GATE 1 — Health endpoint exists:          see above"
echo "  GATE 2 — Smoke test files present:        see above"
echo "  GATE 3 — Required scenarios covered:      see above"
echo "  GATE 4 — Deploy workflow has smoke gate:  see above"
echo "  GATE 5 — Smoke tests pass locally:        see above"
echo ""
echo "  Complete only when ALL gates show PASS."
echo "  After deploy, SMOKE_BASE_URL=<staging-url> pytest smoke/"
echo "============================================================"
```

## What comes next

- **Regression tests** → `regression-tests` skill — nightly full suite

---

## Mandatory: Post-Write Review Gate

After writing tests, **before committing**, run the `test-review` skill:
- External service leak scan (every client in `utils/clients/` mocked in conftest)
- DB safety audit (no production defaults, stable IDs, db_manager restore)
- Duplication scan (no copy-pasted infrastructure across files)
- Mock target verification (patch paths match real source)
- Lint + format + combined suite run

No test changes ship without passing this gate.
