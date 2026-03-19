---
name: resilience-tests
description: >
  Implement resilience tests for a backend service — timeout handling, connection errors,
  malformed responses, 5xx recovery, circuit breakers, and graceful degradation. Use when:
  the user wants to test how the service behaves when dependencies fail, network timeouts
  occur, databases go down, or external APIs return garbage. Trigger on "resilience tests",
  "timeout tests", "failure handling tests", "test connection errors", "test graceful
  degradation", "5xx handling tests", "circuit breaker tests", or "test what happens when
  X goes down". Resilience tests sit between integration and regression in the pipeline —
  they prove the system degrades gracefully rather than catastrophically.
---

# Resilience Tests Skill

## When to Apply (Analyzer decides per-repo)

| Repo type | Apply? | Reason |
|-----------|--------|--------|
| Backend service with external HTTP deps or DB | **Yes** | Dependencies fail in prod — service must degrade gracefully |
| MCP / worker services calling external APIs | **Yes** | Same failure modes |
| Frontend (Next.js, React) | **No** | Error boundaries + retry logic, not resilience suite |
| Proto / schema repos | **No** | No runtime behavior to test |
| Libraries / SDKs | **No** | Consuming service owns its resilience |
| POC / experimental | **No** | Not worth the investment |

**If the Analyzer doesn't flag the repo for resilience, skip this skill entirely.**

## What Resilience Tests Cover

Resilience tests answer: **"What happens when things go wrong?"**

| Category | What to test |
|----------|-------------|
| **Timeouts** | HTTP client timeouts, DB query timeouts, external API timeouts |
| **Connection errors** | DB unreachable, Redis down, external service DNS failure |
| **Malformed responses** | External APIs returning HTML instead of JSON, empty bodies, truncated data |
| **5xx handling** | Upstream 500/502/503 responses, retry behavior, backoff |
| **Partial failures** | One of N dependencies fails — does the rest still work? |
| **Resource exhaustion** | Connection pool full, rate limits hit, disk full |
| **Data corruption** | Invalid/null fields in DB documents, schema mismatches |

## Stack Adaptation

Before writing tests, detect the stack and load the matching context from `contexts/`.

---

## Phase 1 — Audit Failure Points

```bash
# Find all external HTTP calls
grep -rn "httpx\|requests\|aiohttp\|AsyncClient" sdr_backend/ --include="*.py" | grep -v __pycache__ | grep -v test

# Find all DB operations
grep -rn "await.*find\|await.*insert\|await.*update\|await.*delete\|await.*aggregate" sdr_backend/ --include="*.py" | grep -v __pycache__ | grep -v test | head -20

# Find all client classes
grep -rn "class.*Client\|class.*Api\b" sdr_backend/utils/clients/ --include="*.py"

# Find existing error handling
grep -rn "except.*Exception\|except.*Error\|raise HTTP" sdr_backend/ --include="*.py" | grep -v __pycache__ | grep -v test | wc -l
```

Map each external dependency → what happens if it fails → is that tested?

## Phase 2 — Test Structure

```
tests/resilience/
├── __init__.py
├── conftest.py              # Shared fixtures, mock failure helpers
├── test_timeout_handling.py  # HTTP/DB/external timeouts
├── test_connection_errors.py # Unreachable services, DNS failures
├── test_malformed_responses.py # Bad JSON, HTML errors, empty bodies
└── test_http_edge_cases.py   # 5xx, rate limits, retries
```

### conftest.py pattern

```python
import pytest
from unittest.mock import AsyncMock, patch

@pytest.fixture(autouse=True)
def _mock_external_services():
    """Same centralized mock as integration/performance conftest."""
    # ... all external clients mocked
    yield
```

### Test patterns

**Timeout test:**
```python
async def test_scheduler_timeout_returns_graceful_error(client):
    with patch(
        "sdr_backend.utils.clients.scheduler.SchedulerApi.create_scheduler",
        new_callable=AsyncMock,
        side_effect=httpx.TimeoutException("Connection timed out"),
    ):
        res = await client.post("/api/v1/campaigns", ...)
        assert res.status_code in (500, 503, 408)
        body = res.json()
        assert "error" in body or "detail" in body
```

**Connection error test:**
```python
async def test_db_connection_lost_returns_500(client):
    with patch(
        "sdr_backend.repositories.campaign.Campaign.find",
        new_callable=AsyncMock,
        side_effect=ConnectionError("MongoDB connection lost"),
    ):
        res = await client.get("/api/v1/campaigns", ...)
        assert res.status_code == 500
```

**Malformed response test:**
```python
async def test_pdl_returns_html_instead_of_json(client):
    with patch(
        "sdr_backend.utils.clients.pdl.PDLClient.search",
        new_callable=AsyncMock,
        return_value="<html>502 Bad Gateway</html>",
    ):
        res = await client.post("/api/v1/prospects/search", ...)
        assert res.status_code in (500, 502)
```

## Phase 3 — Verification Checklist

- [ ] Every external client has at least one timeout test
- [ ] Every external client has at least one connection error test
- [ ] Critical endpoints handle DB failures gracefully (no unhandled exceptions)
- [ ] AI/LLM endpoints handle empty/null/malformed responses
- [ ] Error responses have consistent format (detail field, status code)
- [ ] No test calls real external services (mocked in conftest)
- [ ] Tests are in `tests/resilience/`, not mixed with unit/integration
- [ ] CI workflow includes `resilience-tests` job

## Phase 4 — CI Wiring

Add to `.github/workflows/ci.yml`:
```yaml
resilience-tests:
    needs: [lint]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: uv sync --dev
      - name: Run resilience tests
        run: uv run pytest tests/resilience/ -v
```

---

## Mandatory: Post-Write Review Gate

After writing tests, **before committing**, run the `test-review` skill:
- External service leak scan (every client in `utils/clients/` mocked in conftest)
- DB safety audit (no production defaults, stable IDs, db_manager restore)
- Duplication scan (no copy-pasted infrastructure across files)
- Mock target verification (patch paths match real source)
- Lint + format + combined suite run

No test changes ship without passing this gate.
