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
Phase 4: Resilience (timeout/5xx/failure handling)
            │
            ▼
Phase 5: Regression wiring (nightly CI + Slack alerts)
            │
            ▼
Phase 6: Verifier (final gate)

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
