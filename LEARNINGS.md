# LEARNINGS.md — Sentinel's Memory

> Each deployment makes Sentinel smarter. This file captures what worked, what broke, and what to do differently next time.

---

## Deployment #1: FastAPI Backend — Unit + Security + Contract + Smoke

**Stack:** FastAPI + Beanie/MongoDB + API Key auth
**Date:** March 2026
**Result:** 2,791 tests, 100% unit coverage, all CI green

### What Worked
- Parallel agents (coverage + integration + smoke) dramatically reduces clock time
- `follow_redirects=True` in httpx is mandatory for FastAPI testing
- mongomock-motor works perfectly for unit tests with no real DB
- Testcontainers MongoDB for integration tests in CI

### What Broke (and fixes)
1. **Catch-all file creation** — agents defaulted to `test_final.py` style dumps. Fix: explicit "NEVER create catch-all files" in SOUL + all agent files.
2. **Hallucinated method names** — Fix: require `grep 'def method_name' source.py` before writing any mock.
3. **Agent timeouts on large suites** — Fix: break work into batches by module, commit after each.
4. **Trailing slash 307 redirects** — Fix: `follow_redirects=True` in every httpx AsyncClient.
5. **Python version gap (local 3.14 vs CI 3.11)** — Fix: treat CI as truth; local errors on version-specific behavior are noise.

### Patterns Discovered
- `pragma: no cover` for unreachable code only — Field validator shadows, module-level startup
- Integration tests: session-scoped DB fixtures + function-scoped cleanup
- Smoke tests: mock DB layer, no real infrastructure
- CI job ordering: unit → security (parallel) → contract → integration

---

## Deployment #1 — Round 2: Integration Tests

**Date:** March 17, 2026
**Result:** 265 integration tests, 62/62 endpoints covered (100%)

### What Worked
- 4 parallel agents by endpoint group (campaigns, customers, emails, sequences)
- One test file per module group; no mixed-concern files
- Fresh branch from `dev` avoided all merge conflict debt

### What Broke (and fixes)
1. **AI endpoint env vars** — `AgentClient` requires both `AI_GATEWAY_BASE_URL` AND `AI_GATEWAY_API_KEY`. Fix: set both in test file env defaults AND CI workflow env block.
2. **Async Redis mock** — `RedisClient.publish` is async; `MagicMock` is not awaitable. Fix: mock entire instance with `AsyncMock()`.
3. **Wrong PR base** — PR opened against `main` when team merges to `dev`. Fix: always run `gh pr list --state merged` to confirm actual merge target before creating a branch.
4. **Path parameter normalization** — coverage audit scripts must strip `{param}` placeholders before matching endpoints.

### Patterns Discovered
- Mock external clients at method level, not low-level HTTP
- `follow_redirects=True` is non-negotiable for FastAPI integration tests
- Fresh branches from actual merge target >>> rebasing old feature branches

---

## Deployment #1 — Round 3: Security Tests

**Date:** March 17, 2026
**Result:** 153 security tests (+90 new), 3 new focused files

### Patterns Discovered
- NoSQL injection in query strings becomes literal string after FastAPI/Pydantic validation — still worth testing to prove protection exists
- `detail=str(e)` error paths can leak internals — test all error-producing endpoints
- Cross-user isolation: verify 404 or 403, not just any non-200
- pip-audit belongs in CI as a workflow step, not just manual checks

---

## Deployment #1 — Round 4: Data Integrity + Performance + Smoke

**Date:** March 17, 2026
**Result:** +67 tests (33 data integrity, 16 performance, 18 smoke)

### What Broke
- Coverage agent overwrote manual fixes to metrics tests. Rule added: read current diff/context before writing.
- 2 tests needed deep rewrites after activation flow changes — skipped with reason rather than shipping broken mocks.

### Rules Added
- Read the current source after every upstream merge — don't rely on memory of what it used to be.
- Skip with a real reason and revisit plan is acceptable. Skip without reason is not.

---

## Deployment #1 — Round 5: Obsolete Skip Guard Cleanup

**Date:** March 18, 2026
**Branch:** `test/fix-skipped-tests`
**Result:** 14 skipped tests restored; PR opened; CI passed on first try

### What Happened
14 tests had been guarded with:
```python
@pytest.mark.skipif(sys.version_info < (3, 13), reason="Workflow mock structure differs on Python 3.11")
```
This guard was added to work around WorkflowApi mock behavior. WorkflowApi was later deleted from the codebase entirely. The guard became obsolete — but CI runs Python 3.11, so all 14 tests silently never executed for months.

### Fix Applied
- Removed all 14 `skipif(sys.version_info < (3, 13))` decorators across 6 files
- Removed now-unused `import sys` lines
- All 14 tests pass on Python 3.11

### Key Learnings
1. **Major deletions leave obsolete guards** — whenever a service, client, or module is removed, search for skip/patch/guard markers tied to it.
2. **Skipped tests are operational debt** — review periodically, especially after refactors.
3. **Version gates are temporary** — treat them as tech debt, not permanent protection.
4. **CI truth > local truth** — local 3.14 issues distracted from 3.11 reality.

### New Standing Rule
After any major module/client deletion: `grep -rn "skipif\|skip\|xfail" tests/` and audit relevance.

---

## Sentinel Strengthening Session

**Date:** March 18, 2026
**Focus:** Multi-repo readiness, autonomous heartbeat, file upgrades

### What Changed
- `SOUL.md` — rewritten for multi-repo ownership model
- `AGENTS.md` — tiered repo portfolio + repo-record schema added
- `HEARTBEAT.md` — proper monitoring loops, schedule, and response format
- `BOOTSTRAP.md` — new repo onboarding checklist (created)
- `contexts/nextjs-prisma.md` — Next.js/TypeScript context (created)
- `memory/2026-03-18.md` — today's session captured
- OpenClaw cron jobs — daily 07:35 IST + weekly Monday wired

### Next Targets
- Onboard `ruh-app-fe` and `ruh-ai-api-gateway` with real local paths + stack scans
- Strengthen agent files (`ci-fix-agent.md`, `integration-agent.md`, etc.) with real playbooks

## 2026-03-19 — admin-service bootstrap

### Repo profile
- **Stack**: FastAPI + SQLAlchemy/PostgreSQL + gRPC + Redis + JWT + OpenTelemetry
- **Branch**: `dev` (default)
- **Package manager**: Poetry
- **CI Python**: 3.11 | Local Python: 3.14
- **Proto compilation**: required for runtime, mocked in tests via `grpc_stubs.py`

### Key learnings
1. **mock.patch path resolution**: `patch("app.services.admin_service.X")` fails if the submodule isn't imported into `app.services` namespace. Fix: pre-import the module in conftest after injecting gRPC stubs.
2. **bcrypt 5.0 vs passlib**: passlib doesn't support bcrypt 5.0+ (`__about__` removed). Pin `bcrypt<5` or use `bcrypt==4.0.1` (already in pyproject.toml).
3. **gRPC services need stub mocking**: No proto files are compiled locally — tests inject `types.ModuleType` stubs for `admin_pb2` and `admin_pb2_grpc` into `sys.modules`.
4. **The repo's only "test" was a manual print script** — zero assertions, not real pytest. Now replaced with 149 proper tests.
5. **Poetry is the package manager** (not pip/uv), CI uses `poetry install --with dev --no-root`.

---

## 2026-03-19 — MCP Server Full Bootstrap

**Stack:** Python MCP Server + Pydantic + httpx backend client
**Date:** March 19, 2026
**Result:** 876 unit tests (100% coverage), 33 smoke tests, contract/security/resilience/integration layers

### What Worked
- uv as package manager — fast, reliable, works in CI without issues
- Tool schema validation as contract tests — natural fit for MCP servers
- BackendClient mock pattern: patch `_request()` once, test all tool methods

### What Broke (and fixes)
1. **Wrong class names in smoke tests** — `EmailTool` doesn't exist, it's `EmailConversationTool`. Fix: always `grep "^class "` before writing import tests.
2. **Pydantic V1 deprecation warnings** flood pytest output, hiding pass/fail summary. Fix: use `-W ignore::DeprecationWarning` or redirect to file.
3. **BackendClient has no `get`/`post` methods** — uses `_request()` internally. Fix: verify actual API surface, don't assume REST-style methods.

### Patterns Discovered
- MCP tool testing: mock BackendClient → call tool method → assert response structure
- Resilience testing for MCP: simulate timeouts, HTTP 5xx, malformed JSON from backend
- uv CI pattern: `uv sync --extra dev` → `uv run --extra dev pytest`

---

## 2026-03-19 — Admin Service Full Bootstrap

**Stack:** FastAPI + SQLAlchemy/PostgreSQL + gRPC + Redis + JWT + OpenTelemetry
**Date:** March 19, 2026
**Result:** 300+ tests (211 unit + 30 contract + 22 resilience + 65 security)

### What Worked
- gRPC stub injection via `types.ModuleType` — clean, no proto compilation needed for tests
- `conftest.py` per suite directory — keeps mock setup isolated
- Security test parametrization — SQL injection / XSS / path traversal payloads as pytest params

### What Broke (and fixes)
1. **Python 3.14 venv missing deps** — grpc, pydantic-core, psycopg2 not installed by poetry on 3.14. Fix: manual `pip install` for local testing, CI on 3.11 is fine.
2. **DatabaseManager initializes at module import** — importing `admin_service` triggers DB connection. Fix: gRPC stub injection + mocking must happen before any app import.
3. **Parallel agents killed by SIGTERM (code 143)** — but file-level work survives. Fix: commit frequently, verify files after agent death.

### Standing Rules Added
- For gRPC services: always create `grpc_stubs.py` shared stub module
- For SQLAlchemy repos: mock `Session.refresh()` with side_effect for create flows
- For multi-DB repos: check `DatabaseManager.__init__` import chain before writing conftest
