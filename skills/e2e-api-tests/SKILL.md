---
name: e2e-api-tests
description: >
  Implement multi-step API end-to-end tests against a live deployed service. Use this skill
  when the user wants to test complete business workflows (not single endpoints), verify
  that create-read-update-delete chains work across services, test post-deploy API flows
  against staging/QA, or validate that side effects (scheduling, notifications, cascading
  deletes) actually happen in a deployed environment. Trigger when the user mentions
  "API E2E tests", "workflow tests", "end-to-end API flows", "test the full journey",
  "multi-step API test", "test against staging", "post-deploy API validation", or
  "business flow tests". This skill differs from integration tests (single endpoints with
  Testcontainers) and smoke tests (health checks). API E2E tests verify that complete
  user journeys work on a real deployed service.
---

# API End-to-End Tests Skill

## Stack Adaptation

Before writing any tests, detect the project's stack and load the matching context:

| Signal | Context File |
|--------|-------------|
| `from fastapi` + `beanie`/`motor` | `contexts/fastapi-beanie.md` |
| `from fastapi` + `sqlalchemy` | `contexts/fastapi-sqlalchemy.md` |
| `from flask` | `contexts/flask-sqlalchemy.md` |
| `from django` | `contexts/django-orm.md` |
| `package.json` + `next` + `prisma` | `contexts/nextjs-prisma.md` |

Read the context file for auth patterns and API conventions specific to this stack.

---

You are an expert backend QA engineer. Your mission: implement API end-to-end tests that verify
complete business workflows against a live deployed service.

**API E2E tests answer: "Do multi-step business workflows actually work on the deployed service?"**

They are NOT:
- **Integration tests** — those test single endpoints with Testcontainers locally
- **Smoke tests** — those check if the service is alive (health, auth, response time)
- **Unit tests** — those test business logic in isolation with mocks

API E2E tests chain multiple API calls into real business flows and verify the entire journey.

---

## Phase 1 — Identify Critical Business Flows

```bash
# Find all route definitions to understand the API surface
grep -r "@app.get\|@app.post\|@app.patch\|@app.delete\|@router" . --include="*.py" -l 2>/dev/null | grep -v test | head -20

# Or for Node.js
grep -r "router.get\|router.post\|app.get\|app.post" . --include="*.ts" --include="*.js" -l 2>/dev/null | grep -v test | head -20

# Check for service layer to understand business logic
find . -path "*/services/*.py" -o -path "*/services/*.ts" 2>/dev/null | grep -v test | head -20
```

Map out the critical flows. Common patterns:

| Flow | Steps |
|---|---|
| User lifecycle | Register → Login → Update profile → Deactivate |
| Resource CRUD | Create → Read → Update → List → Delete → Verify deleted |
| Workflow activation | Create draft → Configure → Activate → Verify side effects |
| Multi-resource | Create parent → Add children → Delete parent → Verify cascade |
| Search/filter | Create N items → Search with filters → Verify results |
| Pagination | Create N items → Page through → Verify totals and ordering |

---

## Phase 2 — Install Dependencies

```bash
pip install \
  httpx \
  pytest \
  pytest-asyncio \
  tenacity
```

For Node.js:
```bash
npm install --save-dev supertest jest
```

---

## Phase 3 — Configure Test Environment

```python
# tests/e2e_api/conftest.py
"""
API E2E test configuration.
Tests run against a live deployed service — NOT against Testcontainers.

Required env vars:
  E2E_BASE_URL   — the deployed service URL (e.g. https://staging.example.com)
  E2E_AUTH_TOKEN  — valid auth credentials for the deployed service (optional, tests skip if missing)

Usage:
  E2E_BASE_URL=https://staging.example.com pytest tests/e2e_api/ -v
"""
import os
import pytest
import httpx
from tenacity import retry, stop_after_delay, wait_fixed, retry_if_exception_type

BASE_URL = os.environ.get("E2E_BASE_URL", "").rstrip("/")
AUTH_TOKEN = os.environ.get("E2E_AUTH_TOKEN", "")


def pytest_configure(config):
    config.addinivalue_line("markers", "e2e_api: multi-step API workflow tests against live service")


@pytest.fixture(scope="session", autouse=True)
def require_base_url():
    """Skip all E2E API tests if no base URL is configured."""
    if not BASE_URL:
        pytest.skip("E2E_BASE_URL not set — skipping API E2E tests")


@pytest.fixture(scope="session", autouse=True)
def wait_for_service():
    """Wait up to 120 seconds for the service to be healthy."""
    if not BASE_URL:
        return

    @retry(
        stop=stop_after_delay(120),
        wait=wait_fixed(5),
        retry=retry_if_exception_type((httpx.ConnectError, httpx.RemoteProtocolError)),
        reraise=True,
    )
    def _wait():
        with httpx.Client(timeout=10) as c:
            res = c.get(f"{BASE_URL}/health")
            assert res.status_code == 200

    print(f"\n  Waiting for service at {BASE_URL}...")
    _wait()
    print(f"  Service ready.")


@pytest.fixture(scope="module")
def client():
    """Shared HTTP client for all tests in a module."""
    with httpx.Client(base_url=BASE_URL, timeout=30) as c:
        yield c


@pytest.fixture(scope="module")
async def async_client():
    """Async HTTP client for async test flows."""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as c:
        yield c


@pytest.fixture(scope="module")
def auth_headers():
    """Auth headers for the deployed service. Skip if not configured."""
    if not AUTH_TOKEN:
        pytest.skip("E2E_AUTH_TOKEN not set")
    return {"Authorization": f"Bearer {AUTH_TOKEN}"}
```

**pytest config:**
```toml
# pyproject.toml — add to markers
[tool.pytest.ini_options]
markers = [
    # ... existing markers ...
    "e2e_api: multi-step API workflow tests against live deployed service",
]
```

**Makefile:**
```makefile
test-e2e-api:
	pytest tests/e2e_api/ -v --timeout=120

test-e2e-api-staging:
	E2E_BASE_URL=$(STAGING_URL) E2E_AUTH_TOKEN=$(STAGING_TOKEN) pytest tests/e2e_api/ -v --timeout=120
```

---

## Phase 4 — File Structure

```
tests/
└── e2e_api/
    ├── conftest.py              ← shared fixtures (client, auth, cleanup)
    ├── test_user_lifecycle.py   ← one file per business flow
    ├── test_resource_crud.py
    ├── test_workflow_activation.py
    ├── test_cascade_operations.py
    └── helpers/
        ├── __init__.py
        ├── api.py               ← thin wrappers for common API calls
        └── cleanup.py           ← test data cleanup utilities
```

**Naming convention:**
- Files: `test_{flow_name}.py` — named after the business flow, not the endpoint
- Classes: `TestUserLifecycle`, `TestCampaignWorkflow`
- Methods: `test_step_N_description` — numbered to show order within flow

---

## Phase 5 — Write API E2E Tests

### Pattern A — Resource CRUD Lifecycle

```python
# tests/e2e_api/test_resource_crud.py
"""
Full CRUD lifecycle: Create → Read → Update → List → Delete → Verify deleted.
Each test method is a step in the flow. Steps share state via class attributes.
"""
import pytest
import httpx

pytestmark = [pytest.mark.e2e_api]


class TestUserCRUDLifecycle:
    """Complete user lifecycle against the deployed service."""

    created_user_id: str = ""

    def test_step_1_create_user(self, client: httpx.Client, auth_headers: dict):
        """Create a user and capture its ID for subsequent steps."""
        res = client.post(
            "/api/users",
            json={"email": "e2e-test@example.com", "password": "Secure123!"},
            headers=auth_headers,
        )
        assert res.status_code == 201, f"Create failed: {res.status_code} — {res.text}"
        body = res.json()
        assert "id" in body
        assert body["email"] == "e2e-test@example.com"
        TestUserCRUDLifecycle.created_user_id = body["id"]

    def test_step_2_read_user(self, client: httpx.Client, auth_headers: dict):
        """Read the created user by ID."""
        user_id = TestUserCRUDLifecycle.created_user_id
        assert user_id, "Step 1 must run first"

        res = client.get(f"/api/users/{user_id}", headers=auth_headers)
        assert res.status_code == 200
        assert res.json()["email"] == "e2e-test@example.com"

    def test_step_3_update_user(self, client: httpx.Client, auth_headers: dict):
        """Update the user and verify the change persists."""
        user_id = TestUserCRUDLifecycle.created_user_id
        res = client.patch(
            f"/api/users/{user_id}",
            json={"display_name": "E2E Test User"},
            headers=auth_headers,
        )
        assert res.status_code == 200
        assert res.json()["display_name"] == "E2E Test User"

    def test_step_4_list_includes_user(self, client: httpx.Client, auth_headers: dict):
        """List endpoint must include the created user."""
        res = client.get("/api/users", headers=auth_headers)
        assert res.status_code == 200
        user_ids = [u["id"] for u in res.json().get("items", res.json().get("data", []))]
        assert TestUserCRUDLifecycle.created_user_id in user_ids

    def test_step_5_delete_user(self, client: httpx.Client, auth_headers: dict):
        """Delete the user."""
        user_id = TestUserCRUDLifecycle.created_user_id
        res = client.delete(f"/api/users/{user_id}", headers=auth_headers)
        assert res.status_code in (200, 204)

    def test_step_6_verify_deleted(self, client: httpx.Client, auth_headers: dict):
        """Confirm the user is no longer accessible."""
        user_id = TestUserCRUDLifecycle.created_user_id
        res = client.get(f"/api/users/{user_id}", headers=auth_headers)
        assert res.status_code == 404
```

### Pattern B — Workflow with Side Effects

```python
# tests/e2e_api/test_workflow_activation.py
"""
Multi-step workflow: Create draft → Configure → Activate → Verify side effects.
Tests that activation actually triggers downstream actions (scheduling, notifications, etc.)
"""
import pytest
import httpx
import time

pytestmark = [pytest.mark.e2e_api]


class TestWorkflowActivation:
    """Test the complete activation workflow with side effect verification."""

    resource_id: str = ""

    def test_step_1_create_draft(self, client: httpx.Client, auth_headers: dict):
        res = client.post(
            "/api/workflows",
            json={"name": "E2E Test Workflow", "type": "sequence"},
            headers=auth_headers,
        )
        assert res.status_code == 201
        body = res.json()
        assert body["status"] == "draft"
        TestWorkflowActivation.resource_id = body["id"]

    def test_step_2_configure(self, client: httpx.Client, auth_headers: dict):
        """Add configuration required before activation."""
        res = client.patch(
            f"/api/workflows/{TestWorkflowActivation.resource_id}",
            json={"schedule": "daily", "target": "all"},
            headers=auth_headers,
        )
        assert res.status_code == 200

    def test_step_3_activate(self, client: httpx.Client, auth_headers: dict):
        """Activate the workflow — this should trigger side effects."""
        res = client.post(
            f"/api/workflows/{TestWorkflowActivation.resource_id}/activate",
            headers=auth_headers,
        )
        assert res.status_code == 200
        assert res.json()["status"] == "active"

    def test_step_4_verify_side_effects(self, client: httpx.Client, auth_headers: dict):
        """Verify that activation created the expected side effects."""
        # Wait briefly for async side effects to propagate
        time.sleep(2)

        res = client.get(
            f"/api/workflows/{TestWorkflowActivation.resource_id}",
            headers=auth_headers,
        )
        assert res.status_code == 200
        body = res.json()
        assert body["status"] == "active"
        # Verify side effects specific to this workflow type
        # e.g., scheduled_at is set, notification was queued, etc.

    def test_step_5_deactivate(self, client: httpx.Client, auth_headers: dict):
        """Deactivate and verify side effects are cleaned up."""
        res = client.post(
            f"/api/workflows/{TestWorkflowActivation.resource_id}/deactivate",
            headers=auth_headers,
        )
        assert res.status_code == 200
        assert res.json()["status"] == "inactive"

    def test_step_6_cleanup(self, client: httpx.Client, auth_headers: dict):
        """Delete test data."""
        res = client.delete(
            f"/api/workflows/{TestWorkflowActivation.resource_id}",
            headers=auth_headers,
        )
        assert res.status_code in (200, 204)
```

### Pattern C — Cascade Delete Verification

```python
# tests/e2e_api/test_cascade_operations.py
"""
Cascade: Create parent → Add children → Delete parent → Verify children deleted.
"""
import pytest
import httpx

pytestmark = [pytest.mark.e2e_api]


class TestCascadeDelete:
    """Verify that deleting a parent resource cascades to children."""

    parent_id: str = ""
    child_ids: list = []

    def test_step_1_create_parent(self, client: httpx.Client, auth_headers: dict):
        res = client.post("/api/projects", json={"name": "E2E Cascade Test"}, headers=auth_headers)
        assert res.status_code == 201
        TestCascadeDelete.parent_id = res.json()["id"]

    def test_step_2_add_children(self, client: httpx.Client, auth_headers: dict):
        parent_id = TestCascadeDelete.parent_id
        TestCascadeDelete.child_ids = []
        for i in range(3):
            res = client.post(
                f"/api/projects/{parent_id}/tasks",
                json={"title": f"Task {i}"},
                headers=auth_headers,
            )
            assert res.status_code == 201
            TestCascadeDelete.child_ids.append(res.json()["id"])
        assert len(TestCascadeDelete.child_ids) == 3

    def test_step_3_delete_parent(self, client: httpx.Client, auth_headers: dict):
        res = client.delete(f"/api/projects/{TestCascadeDelete.parent_id}", headers=auth_headers)
        assert res.status_code in (200, 204)

    def test_step_4_children_also_deleted(self, client: httpx.Client, auth_headers: dict):
        """All child resources should be gone after parent deletion."""
        for child_id in TestCascadeDelete.child_ids:
            res = client.get(f"/api/tasks/{child_id}", headers=auth_headers)
            assert res.status_code == 404, f"Child {child_id} still exists after parent deletion"
```

### Pattern D — Retry for Eventual Consistency

```python
# tests/e2e_api/helpers/api.py
"""Thin wrappers with retry logic for eventually-consistent operations."""
from tenacity import retry, stop_after_delay, wait_exponential, retry_if_result
import httpx


def _not_found(result):
    return result.status_code == 404


@retry(
    stop=stop_after_delay(30),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_result(_not_found),
)
def wait_for_resource(client: httpx.Client, url: str, headers: dict) -> httpx.Response:
    """Poll until a resource exists (for async creation workflows)."""
    return client.get(url, headers=headers)


@retry(
    stop=stop_after_delay(30),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_result(lambda r: r.json().get("status") != "active"),
)
def wait_for_status(client: httpx.Client, url: str, headers: dict, target: str = "active") -> httpx.Response:
    """Poll until a resource reaches a target status."""
    return client.get(url, headers=headers)
```

### Pattern E — Test Data Cleanup

```python
# tests/e2e_api/helpers/cleanup.py
"""Cleanup utilities for test data created during E2E flows."""
import httpx
from typing import Optional


class TestDataTracker:
    """Track created resources for cleanup after tests."""

    def __init__(self):
        self._resources: list[tuple[str, str]] = []  # (url, method)

    def track(self, delete_url: str, method: str = "DELETE"):
        """Register a resource for cleanup."""
        self._resources.append((delete_url, method))

    def cleanup(self, client: httpx.Client, headers: dict):
        """Delete all tracked resources in reverse order (children first)."""
        for url, method in reversed(self._resources):
            try:
                if method == "DELETE":
                    client.delete(url, headers=headers)
            except Exception:
                pass  # Best-effort cleanup
        self._resources.clear()
```

```python
# Usage in conftest.py
@pytest.fixture
def tracker():
    t = TestDataTracker()
    yield t
    # Auto-cleanup after test
    # t.cleanup(client, auth_headers)
```

---

## Phase 6 — Required Flow Coverage

For each critical domain in the application, ensure these flows are tested:

| Flow Type | What It Verifies | Required |
|---|---|---|
| CRUD lifecycle | Create → Read → Update → List → Delete → Verify deleted | Yes, per major resource |
| Auth flow | Register/Login → Authenticated request → Token refresh | Yes, if auth is custom |
| Workflow activation | Draft → Configure → Activate → Verify side effects | Yes, per workflow type |
| Cascade operations | Parent delete → Children deleted | Yes, per parent-child relation |
| Cross-resource | Create A → Create B referencing A → Verify B has A data | Yes, per foreign key |
| Pagination | Create N → Page through → Verify totals | Yes, per list endpoint |
| Error recovery | Create → Trigger error mid-flow → Verify state is consistent | Yes, per critical flow |

---

## Phase 7 — CI Integration

### In deploy.yml (after smoke tests)

```yaml
e2e-api:
  name: API E2E Tests
  runs-on: ubuntu-latest
  needs: smoke  # Only run after smoke passes
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with: { python-version: "3.12" }
    - run: pip install httpx pytest pytest-asyncio tenacity
    - name: Run API E2E tests
      run: pytest tests/e2e_api/ -v --timeout=120
      timeout-minutes: 5
      env:
        E2E_BASE_URL: ${{ needs.deploy.outputs.deploy_url }}
        E2E_AUTH_TOKEN: ${{ secrets.E2E_AUTH_TOKEN }}
    - name: Rollback on E2E failure
      if: failure()
      run: echo "API E2E failed — consider rollback"
```

### In regression.yml (nightly)

```yaml
regression-e2e-api:
  name: API E2E (Nightly)
  runs-on: ubuntu-latest
  needs: regression-smoke
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with: { python-version: "3.12" }
    - run: pip install httpx pytest pytest-asyncio tenacity
    - run: pytest tests/e2e_api/ -v --timeout=120
      env:
        E2E_BASE_URL: ${{ vars.DEV_URL }}
        E2E_AUTH_TOKEN: ${{ secrets.DEV_API_KEY }}
```

---

## Phase 8 — Verification Gates

### GATE 1 — Flow files exist for critical domains

```bash
echo "====== GATE 1: E2E API Test Files ======"
e2e_files=$(find tests/e2e_api -name "test_*.py" 2>/dev/null | wc -l)
[ "$e2e_files" -ge 1 ] \
  && echo "  PASS — $e2e_files E2E API test files" \
  || echo "  FAIL — No tests in tests/e2e_api/"
```

### GATE 2 — Multi-step flows (not single-endpoint tests)

```bash
echo "====== GATE 2: Multi-Step Flows ======"
step_count=$(grep -r "def test_step_" tests/e2e_api/ --include="*.py" 2>/dev/null | wc -l)
[ "$step_count" -ge 3 ] \
  && echo "  PASS — $step_count flow steps found" \
  || echo "  FAIL — E2E tests should have numbered steps (test_step_1, test_step_2, ...)"
```

### GATE 3 — Cleanup present

```bash
echo "====== GATE 3: Test Data Cleanup ======"
cleanup=$(grep -r "cleanup\|delete\|test_step.*cleanup\|test_step.*delete" tests/e2e_api/ --include="*.py" 2>/dev/null | wc -l)
[ "$cleanup" -ge 1 ] \
  && echo "  PASS — Cleanup patterns found: $cleanup" \
  || echo "  FAIL — E2E tests must clean up test data"
```

### GATE 4 — All E2E API tests pass

```bash
echo "====== GATE 4: Test Execution ======"
E2E_BASE_URL=${E2E_BASE_URL:-http://localhost:8000} \
  pytest tests/e2e_api/ -v --timeout=120 2>&1 | tail -5
[ $? -eq 0 ] && echo "  GATE 4: PASS" || echo "  GATE 4: FAIL"
```

### GATE 5 — CI workflow has E2E API job

```bash
echo "====== GATE 5: CI Integration ======"
grep -q "e2e.api\|e2e_api\|E2E_BASE_URL" .github/workflows/deploy.yml 2>/dev/null \
  && echo "  PASS — E2E API wired into deploy.yml" \
  || echo "  FAIL — Add E2E API job to deploy.yml after smoke"
```

---

## Critical Rules

1. **Flows, not endpoints** — each test file is a business workflow, not a single API call
2. **Numbered steps** — `test_step_1_create`, `test_step_2_verify` — shows execution order
3. **State carries forward** — use class attributes to share IDs between steps
4. **Always clean up** — delete test data at the end of every flow
5. **Retry for consistency** — use tenacity for async operations that need time to propagate
6. **Real deployed service** — never import app or use Testcontainers in E2E API tests
7. **Timeout budget** — entire flow must complete within 120 seconds
8. **No flaky assertions** — if something is eventually consistent, use retry, not sleep
9. **Independent flows** — each test class is a self-contained flow, no cross-class dependencies

---

## Where This Fits in the Testing Pyramid

```
On every PR (ci.yml):
  Unit tests        → fast, < 3 min
  Integration tests → real DB via Testcontainers, 3-8 min
  Contract tests    → OpenAPI schema diff, < 2 min
  Security audit    → pip-audit + bandit, < 2 min

On merge to main (deploy.yml):
  Deploy to staging
  Smoke tests       → /health + basic checks, < 60 sec
  API E2E tests     → business workflows, < 2 min     ← THIS SKILL
  Browser E2E       → Playwright flows (future)

Nightly (regression.yml):
  Full suite + API E2E + Slack alert
```

## What comes next

- **Browser E2E tests** → `e2e-browser-tests` skill (Playwright, Page Object Model)
