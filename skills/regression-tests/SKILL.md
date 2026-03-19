---
name: regression-tests
description: >
  Set up regression testing for a backend application — a nightly scheduled full-suite run
  against staging that catches environment drift and silent failures. Use this skill when the user
  wants to configure nightly CI runs, set up regression.yml GitHub Actions workflow, tag bug-fix
  tests to make them traceable, prevent previously-fixed bugs from returning, or validate that
  staging stays in sync with production. Trigger when the user mentions "regression tests Python",
  "nightly test run Python", "regression.yml Python", "scheduled CI tests Python", "test against
  staging Python", "prevent regressions Python", "full suite on schedule Python", "nightly build
  Python", or "catch environment drift Python". Note: regression tests are NOT a new test type —
  they are your existing unit, integration, and contract suite run on a schedule against a real
  environment.
---

# Python Monolith — Regression Tests Skill

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


You are an expert backend QA engineer. Your mission: configure regression testing for a Python
monolith — the nightly scheduled run of the full test suite against staging.

**Key principle: "Regression tests" are not a new test type.**
They are your existing unit + integration + contract suite, run:
1. On every PR (catches regressions before merge)
2. Nightly against staging (catches environment drift between deploys)

The only new work is the `regression.yml` workflow and a tagging convention.

---

## Phase 1 — Understand What You Already Have

```bash
# Verify all test types exist
echo "=== Unit tests ===" && find tests/unit -name "test_*.py" 2>/dev/null | wc -l
echo "=== Integration tests ===" && find tests/integration -name "test_*.py" 2>/dev/null | wc -l
echo "=== Contract tests ===" && find tests/contract -name "test_*.py" 2>/dev/null | wc -l
echo "=== Security tests ===" && find tests/security -name "test_*.py" 2>/dev/null | wc -l

# Verify CI pipeline
ls .github/workflows/

# Verify staging environment is accessible
curl -s -o /dev/null -w "%{http_code}" "${STAGING_URL:-http://localhost:8000}/health" 2>/dev/null \
  || echo "STAGING_URL not set"
```

Pre-requisites for this skill:
- [ ] Unit tests exist (`unit-tests` skill complete)
- [ ] Integration tests exist (`integration-tests` skill complete)
- [ ] Contract tests exist (`contract-tests` skill complete)
- [ ] `ci.yml` PR checks are working
- [ ] `deploy.yml` with smoke tests is in place

---

## Phase 2 — Bug Fix Test Tagging Convention

Every bug fix must be accompanied by a test that would have caught it. Tag these with a comment
so they are traceable back to the issue that introduced them:

```python
# tests/integration/test_orders.py
import pytest

pytestmark = pytest.mark.integration


# regression: GH-1234 — orders were returning items belonging to other users
async def test_get_orders_only_returns_authenticated_users_orders(client, auth_headers_alice, auth_headers_bob):
    """Users must only see their own orders — not other users' orders."""
    # Create an order as Alice
    await client.post(
        "/api/orders",
        json={"item": "Widget", "quantity": 1},
        headers=auth_headers_alice
    )

    # Bob should not see Alice's orders
    res = await client.get("/api/orders", headers=auth_headers_bob)
    assert res.status_code == 200
    assert len(res.json()["items"]) == 0


# regression: GH-1589 — pagination was off-by-one on last page
async def test_items_last_page_has_correct_count(client, admin_headers):
    """Last page of pagination must return the correct remainder, not a full page."""
    # Create exactly 15 items
    for i in range(15):
        await client.post(
            "/api/items",
            json={"name": f"Item {i}"},
            headers=admin_headers
        )

    last_page = await client.get("/api/items?page=2&limit=10", headers=admin_headers)
    assert last_page.status_code == 200
    assert len(last_page.json()["items"]) == 5   # not 10, not 0


# regression: GH-1712 — user emails were not normalized before save, causing duplicate accounts
async def test_create_user_normalizes_email_case(client):
    """Email addresses must be case-normalized to prevent duplicate accounts."""
    await client.post("/api/users", json={"email": "ALICE@EXAMPLE.COM", "password": "Secure123!"})
    res = await client.post("/api/users", json={"email": "alice@example.com", "password": "Secure123!"})
    # Must be rejected as a duplicate, not created as a second account
    assert res.status_code == 409
```

**Tagging policy:**
- Format: `# regression: GH-{issue_number} — {one-line description of the bug}`
- The comment explains what broke and why the test catches it
- These tests live in regular test files — no separate `test_regression.py` needed
- Add `pytest.mark.regression` marker for filtering regression-tagged tests:

```python
# tests/integration/test_orders.py
@pytest.mark.integration
@pytest.mark.regression  # tag so it can be selected separately
async def test_get_orders_only_returns_authenticated_users_orders(client):
    ...
```

---

## Phase 3 — regression.yml Scheduled Workflow

```yaml
# .github/workflows/regression.yml
name: Nightly Regression Suite

on:
  schedule:
    - cron: '0 2 * * *'    # 2:00 AM UTC every night
  workflow_dispatch:
    inputs:
      environment:
        description: 'Target environment'
        required: true
        default: 'staging'
        type: choice
        options: [staging, production-readonly]

jobs:
  regression-unit:
    name: Unit Tests (Regression)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install -r requirements.txt
      - run: pytest -m unit --cov --cov-report=xml
      - uses: codecov/codecov-action@v4
        if: always()
        with:
          files: coverage.xml

  regression-integration:
    name: Integration Tests (Regression)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install -r requirements.txt
      - run: pytest -m integration -p no:xdist -v
        env:
          # Testcontainers manages its own Postgres — no DATABASE_URL needed
          # To test against real staging DB instead (read-only replica):
          # DATABASE_URL: ${{ secrets.STAGING_READONLY_DATABASE_URL }}
          pass: ""

  regression-contract:
    name: Contract Tests (Regression)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install -r requirements.txt
      - run: pytest -m contract -v

  regression-security:
    name: Security Scan (Regression)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install pip-audit bandit
      - run: pip-audit
      - run: bandit -r app/ src/ -ll -ii 2>/dev/null || true

  notify-on-failure:
    name: Notify on Failure
    runs-on: ubuntu-latest
    needs: [regression-unit, regression-integration, regression-contract, regression-security]
    if: failure()
    steps:
      - name: Send Slack alert
        uses: slackapi/slack-github-action@v1
        with:
          channel-id: ${{ secrets.SLACK_ALERTS_CHANNEL }}
          slack-message: |
            ❌ *Nightly Regression Failed* — ${{ github.repository }}
            Branch: `${{ github.ref_name }}`
            Run: ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}
        env:
          SLACK_BOT_TOKEN: ${{ secrets.SLACK_BOT_TOKEN }}
```

---

## Phase 4 — Pre-Release Regression Gate

Before any production release, run the full regression suite manually:

```yaml
# .github/workflows/release.yml
name: Production Release

on:
  workflow_dispatch:
    inputs:
      version:
        description: 'Release version (e.g. v1.4.2)'
        required: true

jobs:
  pre-release-regression:
    name: Pre-Release Regression Gate
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install -r requirements.txt
      - run: pytest -m unit --cov --cov-fail-under=80
      - run: pytest -m integration -p no:xdist -v
      - run: pytest -m contract -v
      - run: pip-audit
      - name: Run smoke tests against staging
        run: pytest smoke/ -v --timeout=60
        env:
          SMOKE_BASE_URL: ${{ secrets.STAGING_URL }}
          SMOKE_AUTH_TOKEN: ${{ secrets.SMOKE_AUTH_TOKEN }}

  deploy-production:
    name: Deploy to Production
    runs-on: ubuntu-latest
    needs: pre-release-regression    # blocks on regression failure
    environment: production          # requires manual approval in GitHub
    steps:
      - name: Deploy
        run: echo "Deploying ${{ inputs.version }} to production"
```

---

## Phase 5 — What Regression Tests Catch That CI Doesn't

| Issue | Caught by PR CI | Caught by Nightly Regression |
|---|---|---|
| Code logic bug introduced in PR | ✅ | ✅ |
| Staging env variable misconfigured | ❌ | ✅ |
| DB migration applied with drift | ❌ | ✅ |
| pip dependency broke overnight | ❌ | ✅ |
| Secret expired in staging | ❌ | ✅ |
| Memory leak over time | ❌ | ✅ (via duration monitoring) |
| Schema change in downstream service | ❌ | ✅ (via contract tests vs staging) |

---

## Phase 6 — Tracking Regression Tags

```bash
# List all regression-tagged tests with their issue numbers
echo "=== Regression-tagged tests ==="
grep -r "# regression:" tests/ --include="*.py" -n | \
  sed 's/.*# regression: //' | \
  sort

# Count regression tests per file
echo ""
echo "=== Regression test count per file ==="
grep -r "# regression:" tests/ --include="*.py" -l | while read f; do
  count=$(grep -c "# regression:" "$f")
  echo "  $count  $f"
done | sort -rn

# List by GitHub issue
echo ""
echo "=== By issue number ==="
grep -r "# regression: GH-" tests/ --include="*.py" -h | \
  grep -oP 'GH-\d+' | sort -V | uniq -c | sort -rn
```

---

## Phase 7 — Verification Gates

### GATE 1 — Prerequisite test suites in place

```bash
echo "====== GATE 1: Prerequisite Test Suites ======"
unit=$(find tests/unit -name "test_*.py" 2>/dev/null | wc -l)
integration=$(find tests/integration -name "test_*.py" 2>/dev/null | wc -l)
contract=$(find tests/contract -name "test_*.py" 2>/dev/null | wc -l)

[ "$unit" -ge 1 ] && echo "  [PASS] Unit tests: $unit files" || echo "  [FAIL] No unit tests — complete unit-tests first"
[ "$integration" -ge 1 ] && echo "  [PASS] Integration tests: $integration files" || echo "  [FAIL] No integration tests — complete integration-tests first"
[ "$contract" -ge 1 ] && echo "  [PASS] Contract tests: $contract files" || echo "  [FAIL] No contract tests — complete contract-tests first"
```

### GATE 2 — regression.yml exists with schedule

```bash
echo "====== GATE 2: Regression Workflow ======"
[ -f ".github/workflows/regression.yml" ] \
  && echo "  [PASS] regression.yml exists" \
  || echo "  [FAIL] Missing regression.yml"

grep -q "schedule" .github/workflows/regression.yml 2>/dev/null \
  && echo "  [PASS] Schedule trigger present" \
  || echo "  [FAIL] No schedule in regression.yml"

grep -q "workflow_dispatch" .github/workflows/regression.yml 2>/dev/null \
  && echo "  [PASS] Manual trigger present" \
  || echo "  [WARN] No workflow_dispatch — add for pre-release runs"
```

### GATE 3 — Bug fixes are tagged

```bash
echo "====== GATE 3: Regression Tags ======"
tagged=$(grep -r "# regression: GH-" tests/ --include="*.py" 2>/dev/null | wc -l)
[ "$tagged" -ge 1 ] \
  && echo "  [PASS] $tagged regression-tagged tests found" \
  || echo "  [WARN] No tagged tests — add '# regression: GH-XXXX' to bug-fix tests"
```

### GATE 4 — Full suite passes

```bash
echo "====== GATE 4: Full Suite Execution ======"
pytest -m unit --cov --cov-fail-under=80 -q 2>&1 | tail -2 && \
pytest -m integration -p no:xdist -q 2>&1 | tail -2 && \
pytest -m contract -q 2>&1 | tail -2
[ $? -eq 0 ] && echo "  GATE 4: PASS" || echo "  GATE 4: FAIL — fix failures before enabling nightly run"
```

---

## Final Summary

```bash
echo ""
echo "============================================================"
echo "  PY MONOLITH REGRESSION TESTS — COMPLETION REPORT"
echo "============================================================"
echo "  GATE 1 — All prerequisite suites present: see above"
echo "  GATE 2 — regression.yml with schedule:    see above"
echo "  GATE 3 — Bug fixes tagged:                see above"
echo "  GATE 4 — Full suite passes:               see above"
echo ""
echo "  Complete only when ALL gates show PASS."
echo "  Remember: regression tests = existing suite on a schedule."
echo "  The nightly run catches what CI cannot: environment drift."
echo "============================================================"
```

## The Complete Python Testing Stack

When all skills are complete, this is the full picture:

```
On every PR (ci.yml):
  Unit tests        → fast, < 3 min, blocks merge
  Integration tests → real Postgres via Testcontainers, 3–8 min, blocks merge
  Contract tests    → OpenAPI schema diff, < 2 min, blocks merge
  Security audit    → pip-audit + bandit, < 2 min, blocks merge

On merge to main (deploy.yml):
  Deploy to staging
  Smoke tests       → /health + 2–3 checks, < 60 sec, triggers rollback

Nightly at 2am (regression.yml):
  Full suite vs staging → catches environment drift
  Failure → Slack alert to team

Before production release (release.yml):
  Full regression gate + manual approval → deploy to production
```
