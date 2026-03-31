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

### 3. Component Testing Agent (Frontend Only)
```
Role:       Write frontend component tests using Vitest + React Testing Library
Trigger:    Auto during frontend bootstrap, or when component coverage drops
Skill:      skills/component-tests/SKILL.md
Timeout:    1800s (30min)
```

### 4. Integration Agent
```
Role:       Build real-flow request→service→DB coverage
Trigger:    Auto after unit, or /integrate
Method:     httpx / framework client + Testcontainers or stack equivalent
Timeout:    1800s (30min)
```

### 5. Contract Agent
```
Role:       Lock API/schema/protocol contracts and diff in CI
Trigger:    Auto after integration, or /contract
Timeout:    900s (15min)
```

### 6. Security Agent
```
Role:       Auth boundaries, injection, headers, dependency scanning
Trigger:    Auto or /secure
Timeout:    900s (15min)
```


### 7. Resilience Agent
```
Role:       Test graceful degradation — timeouts, connection errors, malformed responses,
            5xx recovery, partial failures, resource exhaustion
Trigger:    Auto after integration + security, or /resilience
Skill:      skills/resilience-tests/SKILL.md
Timeout:    900s (15min)
```
### 8. Smoke Agent
```
Role:       Post-deploy confidence checks under 30s
Trigger:    Auto or /smoke
Timeout:    900s (15min)
```

### 9. E2E Agent
```
Role:       Browser-critical flows via Playwright — POM, screenshots, CI artifacts
Trigger:    /e2e
Timeout:    1800s (30min)
```

### 10. Regression Agent
```
Role:       Nightly workflow setup, scheduled verification, regression response
Trigger:    Auto or /regression
Timeout:    900s (15min)
```

### 11. CI Fix Agent
```
Role:       Diagnose failed CI runs, identify root cause, apply targeted fix
Trigger:    Auto when CI/regression fails, or /fix-ci
Timeout:    1800s (30min)
```

### 12. Verifier Agent
```
Role:       Final pass — run edited suites, validate green state, summarize
Trigger:    Auto after all other agents complete
Timeout:    1800s (30min)
```

### 13. Review Agent (Post-Write Quality Gate)
```
Role:       Mandatory review after any test writing — dedup, mock verification, 
            DB safety, external service leak scan, lint, isolation check
Trigger:    Auto after every test-writing agent completes, or /review-tests
Skill:      skills/test-review/SKILL.md
Timeout:    600s (10min)
```

### 14. PR Review Agent (Team PR Guardian)
```
Role:       Review PRs from team members — coverage impact, security scan,
            breaking changes, pattern enforcement, test quality audit
Trigger:    Heartbeat (checks gh pr list), or /review-pr <number>
Output:     PR review comment with P1/P2/P3 findings
Rules:      Flag only — never auto-fix team PRs. Never approve or merge.
Timeout:    900s (15min)
```

---

## Spawn Order

Matches the canonical CI pipeline (see `github-pipeline` skill):

```
Phase 0: Analyzer (detect stack, produce test plan)
            │
Phase 1: Lint + Type Check (FIRST GATE — blocks everything)
            │
    ┌───────┼──────────────┬──────────────┬────────────────┐
    ▼       ▼              ▼              ▼                ▼
Phase 2: Coverage    Integration  Security-Tests  Security-Audit  SAST
         (unit +     (real DB)    (auth/injection) (bandit/audit) (semgrep)
          component*)
    │         │
    ▼         ▼
Phase 3: Contract (needs unit + integration to pass first)
            │
            ▼
Phase 4: Resilience (IF backend with external deps — skip for frontends/proto/libs)
            │
            ▼
Phase 5: Regression wiring (nightly CI + SAST + DAST + Slack alerts)
            │
            ▼
Phase 6: Review (post-write quality gate — dedup, mock audit, DB safety, lint)
            │
            ▼
Phase 7: Verifier (final gate)

─── POST-DEPLOY (separate pipeline) ───

Deploy → Smoke (real HTTP) → E2E (browser/journey) → DAST (OWASP ZAP)
```

*Component tests apply to frontend repos only (Vitest + Testing Library).

**Key ordering rules:**
- Lint/type-check is ALWAYS the first gate
- Unit + Integration + Security-Tests + Security-Audit + SAST run in parallel (all need lint to pass)
- Contract runs AFTER unit + integration (needs passing tests to validate schema)
- Smoke + E2E + DAST run post-deploy against real URL, NOT in PR pipeline
- E2E only runs if smoke passes; DAST only runs if E2E passes
- For frontend bootstrap: component tests run alongside unit in Phase 2

---

## Universal Agent Rules

1. **NEVER create catch-all test files** (`test_final.py`, `test_remaining.py`, `test_100pct.py`)
2. **Tests go in the correct module file** — source-aligned, no dumping grounds
3. **Verify method names exist** before writing mocks or patch targets
4. **Read the current source first** — especially after upstream merges
5. **Run tests after every edit** — edited file first, then impacted suite
6. **No hallucinated APIs** — if the method is gone, update the test strategy
7. **Use fresh branches from the real merge target** (`dev` vs `main` matters)
8. **Create a Jira ticket on the TT board before first commit. All commits: `TT-XXX description`**
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
| sdr-backend | `/home/hitesh/sdr-backend` | `ruh-ai/sdr-backend` | FastAPI + Beanie/MongoDB + uv | `dev` | P1 |
| inbox-rotation-service | `/home/hitesh/inbox-rotation-service` | `ruh-ai/inbox-rotation-service` | FastAPI + PyMongo + Poetry | `dev` | P1 |

### Tier 2 — Important Supporting Repos

| Repo | Local Path | GitHub | Stack | Branch | Priority |
|------|------------|--------|-------|--------|----------|
| ruh-ai-admin-service | `/home/hitesh/ruh-ai-admin-service` | `ruh-ai/ruh-ai-admin-service` | gRPC + SQLAlchemy/Postgres + Poetry | `dev` | P2 |
| sdr-management-mcp | `/home/hitesh/sdr-management-mcp` | `ruh-ai/sdr-management-mcp` | FastMCP + Pydantic + httpx + uv | `dev` | P2 |
| ruh-super-admin-fe | _TBD_ | `ruh-ai/ruh-super-admin-fe` | TypeScript frontend | `dev` | P2 |
| proto-definitions | _TBD_ | `ruh-ai/proto-definitions` | Protocol/schema | `dev` | P2 |
| smtp-imap-mcp | `/home/hitesh/smtp-imap-mcp` | `ruh-ai/smtp-imap-mcp` | FastAPI + Python | `main` | P2 |

### Tier 3 — Experimental / Skip Unless Requested
- `ruh-ai/people-data-labs-poc`
- `ruh-ai/openclaw-ruh`
- `ruh-ai/ruh-skills`

---

## Connected Repo Record Schema

```yaml
repo: ruh-ai/<repo-name>
local_path: ~/repos/your-repo
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

## Coverage / Quality Targets

See SOUL.md for detailed coverage rules. Summary:
- **Unit: 100% mandatory** — enforced via `--cov-fail-under=100`
- Integration: all key CRUD + error codes + auth boundaries
- Contract: baseline locked and diffed in CI
- Security: headers, authz, authn, injection, dependency audit
- Smoke + E2E: post-deploy only (`post-deploy.yml`), never in CI pipeline
- Regression: nightly scheduled full suite

---

## Critical Learning: External Service Mocking (PR #439 Pattern)

**Rule:** Integration and performance tests must NEVER call real external services — not even their constructors.

**Pattern:** All external service mocks go in a centralized `_mock_external_services` autouse fixture in the suite's `conftest.py`:

```python
@pytest.fixture(autouse=True)
def _mock_external_services():
    with (
        patch("your_app.utils.clients.external_a.ExternalApiA.call", ...),
        patch("your_app.utils.clients.external_b.ExternalApiB.fetch", ...),
        patch("your_app.utils.clients.third_party.ThirdPartyClient.__init__", lambda self: None),
        # Add ALL external clients here — never in individual test files
    ):
        yield
```

**Why:** Settings singletons get poisoned across test suites. Per-file fixtures are fragile and easy to miss. Centralized conftest fixtures guarantee no test ever leaks to real services.

**Applies to:** `tests/integration/conftest.py`, `tests/performance/conftest.py`, and any new test suite that uses real DB (Testcontainers) but needs external services mocked.
