# Sentinel — Agent Team Configuration

> Built by Hitesh Goyal & Sentinel | Powered by OpenClaw

## Philosophy

Sentinel never works alone. Complex testing is split into specialized agents with clear scopes, fast feedback loops, and strict rules about code organization.

---

## Agent Definitions

### 1. Analyzer Agent
```
Role:       Scan repository, detect stack, map CI, produce phased test plan
Trigger:    /scan <repo-url-or-path> [branch:name]
Output:     Stack summary, risk map, missing layers, recommended spawn order
Timeout:    300s (5min)
```

### 2. Coverage Agent (Unit Tests)
```
Role:       Push unit coverage using correct file placement
Trigger:    /cover [target:100]
Method:     Read coverage gaps, inspect source, add tests in correct module file
Timeout:    1800s (30min)
```

### 3. Integration Agent
```
Role:       Build real-flow request→service→DB coverage
Trigger:    Auto after unit, or /integrate
Method:     httpx / framework client + Testcontainers or stack equivalent
Timeout:    1800s (30min)
```

### 4. Contract Agent
```
Role:       Lock API/schema/protocol contracts and diff in CI
Trigger:    Auto after integration, or /contract
Timeout:    900s (15min)
```

### 5. Security Agent
```
Role:       Auth boundaries, injection, headers, dependency scanning
Trigger:    Auto or /secure
Timeout:    900s (15min)
```


### 5b. Resilience Agent
```
Role:       Test graceful degradation — timeouts, connection errors, malformed responses,
            5xx recovery, partial failures, resource exhaustion
Trigger:    Auto after integration + security, or /resilience
Skill:      skills/resilience-tests/SKILL.md
Timeout:    900s (15min)
```
### 6. Smoke Agent
```
Role:       Post-deploy confidence checks under 30s
Trigger:    Auto or /smoke
Timeout:    900s (15min)
```

### 7. E2E Agent
```
Role:       Browser-critical flows via Playwright — POM, screenshots, CI artifacts
Trigger:    /e2e
Timeout:    1800s (30min)
```

### 8. Regression Agent
```
Role:       Nightly workflow setup, scheduled verification, regression response
Trigger:    Auto or /regression
Timeout:    900s (15min)
```

### 9. CI Fix Agent
```
Role:       Diagnose failed CI runs, identify root cause, apply targeted fix
Trigger:    Auto when CI/regression fails, or /fix-ci
Timeout:    1800s (30min)
```

### 10. Verifier Agent
```
Role:       Final pass — run edited suites, validate green state, summarize
Trigger:    Auto after all other agents complete
Timeout:    1800s (30min)
```

### 11. Review Agent (Post-Write Quality Gate)
```
Role:       Mandatory review after any test writing — dedup, mock verification, 
            DB safety, external service leak scan, lint, isolation check
Trigger:    Auto after every test-writing agent completes, or /review-tests
Skill:      skills/test-review/SKILL.md
Timeout:    600s (10min)
```

---

## Spawn Order

Matches the CI pipeline from `ruh-ai/communication-channel-service`:

```
Phase 0: Analyzer (detect stack, produce test plan)
            │
Phase 1: Lint + Type Check (FIRST GATE — blocks everything)
            │
    ┌───────┼──────────────┐
    ▼       ▼              ▼
Phase 2: Coverage   Integration   Security
    (unit tests)  (real DB)     (auth/injection)
    │         │           │
    ▼         ▼           ▼
Phase 3: Contract (needs unit + integration to pass first)
            │
            ▼
Phase 4: Resilience (IF backend with external deps — skip for frontends/proto/libs)
            │
            ▼
Phase 5: Regression wiring (nightly CI + Slack alerts)
            │
            ▼
Phase 6: Review (post-write quality gate — dedup, mock audit, DB safety, lint)
            │
            ▼
Phase 7: Verifier (final gate)

─── POST-DEPLOY (separate pipeline) ───

Deploy → Smoke (real HTTP) → E2E (browser/journey)
```

**Key ordering rules:**
- Lint/type-check is ALWAYS the first gate
- Unit + Integration + Security run in parallel (all need lint to pass)
- Contract runs AFTER unit + integration (needs passing tests to validate schema)
- Smoke + E2E run post-deploy against real URL, NOT in PR pipeline
- E2E only runs if smoke passes

---

## Universal Agent Rules

1. **NEVER create catch-all test files** (`test_final.py`, `test_remaining.py`, `test_100pct.py`)
2. **Tests go in the correct module file** — source-aligned, no dumping grounds
3. **Verify method names exist** before writing mocks or patch targets
4. **Read the current source first** — especially after upstream merges
5. **Run tests after every edit** — edited file first, then impacted suite
6. **No hallucinated APIs** — if the method is gone, update the test strategy
7. **Use fresh branches from the real merge target** (`dev` vs `main` matters)
8. **Commit after each successful phase**
9. **Update memory when a reusable lesson is found**
10. **Prefer fewer larger coherent edits over noisy one-line churn**
11. **Run test-review skill before committing** — no test changes ship without passing the post-write quality gate
12. **Infrastructure code belongs in conftest.py only** — never duplicate DB setup, mock fixtures, or client factories across test files
13. **Every external client in source must be mocked in conftest** — scan `utils/clients/` and verify each class appears in `_mock_external_services`

---

## Connected Repos

### Tier 1 — Active Monitoring Targets

| Repo | Local Path | GitHub | Stack | Branch | Priority |
|------|------------|--------|-------|--------|----------|
| sdr-backend | `~/Desktop/Ruh Development/Repos/sdr-backend` | `ruh-ai/sdr-backend` | FastAPI + Beanie/MongoDB | `dev` | P1 |
| ruh-app-fe | _TBD local clone_ | `ruh-ai/ruh-app-fe` | Next.js / TypeScript | TBD | P1 |
| ruh-ai-api-gateway | _TBD local clone_ | `ruh-ai/ruh-ai-api-gateway` | Python backend | TBD | P1 |

### Tier 2 — Important Supporting Repos

| Repo | Local Path | GitHub | Stack | Branch | Priority |
|------|------------|--------|-------|--------|----------|
| ruh-ai-admin-service | _TBD_ | `ruh-ai/ruh-ai-admin-service` | Python backend | TBD | P2 |
| ruh-super-admin-fe | _TBD_ | `ruh-ai/ruh-super-admin-fe` | TypeScript frontend | TBD | P2 |
| sdr-management-mcp | _TBD_ | `ruh-ai/sdr-management-mcp` | Python service | TBD | P2 |
| proto-definitions | _TBD_ | `ruh-ai/proto-definitions` | Protocol/schema | TBD | P2 |

### Tier 3 — Experimental / Skip Unless Requested
- `ruh-ai/people-data-labs-poc`
- `ruh-ai/openclaw-ruh`
- `ruh-ai/ruh-skills`

---

## Connected Repo Record Schema

```yaml
repo: ruh-ai/sdr-backend
local_path: ~/Desktop/Ruh Development/Repos/sdr-backend
primary_branch: dev
stack: fastapi-beanie
ci_workflow: CI Tests
regression_workflow: Nightly Regression Suite
coverage_target_unit: 100
smoke_enabled: true
e2e_enabled: false
notify: slack + Hitesh
status: active
```

---

## Coverage / Quality Targets (Defaults)

- Unit: **80% minimum**, 100% preferred for critical Python services
- Integration: all key CRUD + error codes + auth boundaries
- Contract: baseline locked and diffed in CI
- Security: headers, authz, authn, injection, dependency audit
- Smoke: post-deploy checks in <30s
- E2E: critical user journeys only, stable and maintainable
- Regression: nightly scheduled run with visible failure path

---

## Critical Learning: External Service Mocking (PR #439 Pattern)

**Rule:** Integration and performance tests must NEVER call real external services — not even their constructors.

**Pattern:** All external service mocks go in a centralized `_mock_external_services` autouse fixture in the suite's `conftest.py`:

```python
@pytest.fixture(autouse=True)
def _mock_external_services():
    with (
        patch("sdr_backend.utils.clients.scheduler.SchedulerApi.create_scheduler", ...),
        patch("sdr_backend.utils.clients.trigger.TriggerApi.create_trigger", ...),
        patch("sdr_backend.utils.clients.inbox_rotation.InboxRotationApi.get_warmup_status", ...),
        patch("sdr_backend.utils.clients.agent_client.AgentClient.__init__", lambda self: None),
        # Add ALL external clients here — never in individual test files
    ):
        yield
```

**Why:** Settings singletons get poisoned across test suites. Per-file fixtures are fragile and easy to miss. Centralized conftest fixtures guarantee no test ever leaks to real services.

**Applies to:** `tests/integration/conftest.py`, `tests/performance/conftest.py`, and any new test suite that uses real DB (Testcontainers) but needs external services mocked.
