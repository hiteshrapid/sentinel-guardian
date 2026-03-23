# LEARNINGS.md — Distilled Patterns

> Reusable lessons extracted from deployments. One-time incidents live in memory/.
> If a pattern becomes a permanent rule, move it to SOUL.md and remove from here.

---

## Python Testing Patterns

### Environment & Config
- `os.environ.get("KEY") or "default"` — GitHub Actions passes `""` for unset secrets, not `None`. The `get()` default only triggers on `None`. Always use `or`.
- `--strict-config` in pytest.ini means ALL workflow steps need ALL plugins installed (e.g., `pytest-asyncio`), even for sync-only suites.
- Python version gaps (local 3.14 vs CI 3.11) — trust CI as truth. Local-only failures on version-specific behavior are noise.

### Mocking
- Read current source before mocking — `grep 'def method_name' source.py` before writing any mock. Methods get renamed/deleted.
- Mock external clients at method level, not low-level HTTP. Patch `_request()` or `__init__`, not `httpx.post`.
- `AsyncMock` required for async methods (e.g., `RedisClient.publish`). `MagicMock` is not awaitable.
- Centralize external service mocks in `conftest.py` autouse fixtures — never scatter across test files.
- `AgentClient.__init__` and similar constructors that validate env vars will blow up in CI without mocks — even if the test expects a 404.

### ORM Gotchas
- Beanie/MongoEngine/SQLAlchemy: `!= True` is NOT the same as `is not True`. ORMs overload `!=` for query building. Always `# noqa: E712`.
- MongoDB pipeline bugs hide behind mocked aggregate results. Integration tests with seeded data are the only reliable catch.
- Test DB name must NEVER default to production DB name.

### File Organization
- NEVER create catch-all test files (`test_final.py`, `test_remaining.py`, `test_100pct.py`)
- Tests go in module-aligned files: `app/services/foo.py` → `tests/unit/test_foo.py`
- `conftest.py` per suite directory — keeps mock setup isolated

### CI Traps
- FastAPI trailing slash → 307 redirect. Use `follow_redirects=True` in httpx everywhere.
- `pip-audit` on private packages → filter with `grep -v "$PACKAGE_NAME"` before auditing.
- `ruff target-version` must match project's Python version, not default `py38`.
- `ruff --unsafe-fixes` can add wrong `match=` patterns — always verify against actual runtime output.
- For source code `raise` without `from err` (B904): add to ruff ignore, don't fix in test PRs.

## Stack-Specific Patterns

### FastAPI + Beanie/MongoDB
- `mongomock-motor` for unit tests, Testcontainers for integration
- Session-scoped DB fixtures + function-scoped cleanup
- `follow_redirects=True` non-negotiable

### FastAPI + SQLAlchemy/PostgreSQL + gRPC
- gRPC services: create `grpc_stubs.py` with `types.ModuleType` stubs, inject into `sys.modules` before app import
- `DatabaseManager` may initialize at module import — mock before any app import
- `Session.refresh()` needs `side_effect` mock for create flows
- Pin `bcrypt<5` (passlib incompatible with 5.0+)

### MCP Servers (FastMCP)
- Tool names are freeform strings (e.g., "Creating or Updating a Campaign") — extract from source with `grep -rn 'name="' sdr_mcp/tools/`, never guess
- `BackendClient` uses `_request()` internally, not `get`/`post` methods
- Health check: hit `/mcp` with initialize payload, not `/health`
- `pytest.mark.timeout(120)` requires `timeout` in pytest markers list with `--strict-markers`

## Workflow Patterns

### Pre-Push Validation
- "Run locally" means simulating CI dep install, not running in fully-loaded dev env
- Use localhost for pre-merge validation, live dev for post-merge
- `pytest --collect-only` passing doesn't mean tests pass — always run them

### PR Discipline
- Always `gh pr list` before creating fix branches — avoid duplicate PRs
- One Sentinel PR per repo max
- Never merge or auto-merge without explicit instruction
- After major module deletions: `grep -rn "skipif\|skip\|xfail" tests/` and audit relevance

### CI Debugging
- When security test fails because tool is missing, run the tool locally — may reveal real CVEs
- Nightly failures are usually workflow/config-contract issues, not real regressions
- Missing `statusCheckRollup` across many PRs = workflow triggers or branch protection need review

## 2026-03-23 — Heartbeat: smtp-imap-mcp — CI fix (lint gate)

**What happened:** PR #5 CI failed at lint-typecheck gate — ruff F403/F405 on `src/server.py` star imports.
**Root cause:** `src/server.py` uses `from .constants.schema import *` and `from .services.email_provider import *` — pre-existing project pattern, not a test file issue. ruff correctly flagged them but they're intentional.
**Fix applied:** Added `[tool.ruff.lint] per-file-ignores = {"src/server.py" = ["F403", "F405"]}` to pyproject.toml.
**Learning:** When bootstrapping a repo that has pre-existing star imports, add per-file-ignores for source files BEFORE pushing the PR, not after CI fails.

## 2026-03-23 — Heartbeat: sdr-management-mcp — Post-deploy smoke broken

**What happened:** Post-deploy smoke job failing with `pytest: error: unrecognized arguments: --timeout=30`.
**Root cause:** `pytest-timeout` was not in pyproject.toml dev/test deps, but post-deploy and regression workflows used `--timeout=30` / `--timeout=300` flags.
**Fix applied:** Added `pytest-timeout>=2.3.0` to both dev and test optional-dependencies. PR #43.
**Learning:** When writing CI workflows with `--timeout` flags, always check `pytest-timeout` is in deps. Add it to the pyproject as part of the bootstrap, not discovered post-deploy.

## 2026-03-23 — Heartbeat: ruh-ai-admin-service — Security Audit CI failure

**What happened:** Security audit step failing with `The requested command export does not exist.`
**Root cause:** Poetry 2.x removed the `poetry export` command. Workflow used `poetry export -f requirements.txt` to generate requirements for pip-audit.
**Fix applied:** Try `pip install poetry-plugin-export` first; fall back to `poetry run pip freeze` if export fails. Handles both Poetry 1.x and 2.x.
**Learning:** `poetry export` is removed in Poetry 2.x. Always use `poetry-plugin-export` or `poetry run pip freeze` as fallback. For new repos, prefer `uv export` (uv always supports it).

## 2026-03-23 — Heartbeat: inbox-rotation-service — Nightly regression security failure

**What happened:** Nightly regression security tests failed with `inbox-rotation: Dependency not found on PyPI and could not be audited`.
**Root cause:** pip-audit runs against the full environment including the private `inbox-rotation` package, which isn't on PyPI. The fix was already committed to dev (PR #54 merged earlier).
**Fix applied:** None needed — fix already on dev. Tonight's nightly will pass.
**Learning:** pip-audit always tries to audit the local package itself. The `"dependency not found on PyPI"` check in `test_dependency_audit.py` handles this correctly once merged.

## 2026-03-23 — Bootstrap: ruh-super-admin-fe — CI fix round

**What happened:** First CI push for ruh-super-admin-fe bootstrap PR #139 failed on two jobs:
1. Security Audit: `npm audit` rejected (no package-lock.json — Yarn project)
2. Lint + Type Check: `tsc` failed with TS5101 (baseUrl deprecated in TS 6.x) and TS2882/TS2591 errors (CSS imports + process global + NodeJS.Timeout require @types/node in TS 6.x)

**Root causes:**
- Yarn projects don't have package-lock.json → use `yarn audit --groups dependencies --level high`
- TypeScript 6.x removed implicit Node.js globals — `process.env`, `NodeJS.Timeout` require explicit `@types/node`
- CSS side-effect imports now require a type declaration in TS 6.x (`declare module "*.css"`)
- `@types/node` is 10MB+ — couldn't install locally due to disk (19/20GB used); must be installed explicitly in CI

**Fix applied:**
- Created `src/css.d.ts` (CSS module type stub)
- Created `src/types/node-globals.d.ts` (minimal NodeJS.Timeout + process stubs — committed to repo)
- Added `ignoreDeprecations: "6.0"` to tsconfig.json
- CI workflow: install `@types/node` as explicit step before typecheck
- CI workflow: switch to `yarn audit` for security scanning
- Bumped next 15.3.3→15.3.9 (3 CVEs) and axios ^1.10→^1.13.5 (2 CVEs)

**Learning:**
- **TypeScript 6.x requires `@types/node` explicitly** — no longer implicit. Bootstrap new projects by checking TS version first; if >=6.0, ensure @types/node is in devDependencies or committed stubs exist.
- **Always use `yarn audit` (not `npm audit`) for Yarn projects** — npm audit requires package-lock.json, which Yarn projects don't have.
- **Disk usage on the VPS is at 95%** — avoid large package installs locally; rely on CI for heavy dependencies. Consider cleaning /home/hitesh/.cache/pypoetry and yarn cache regularly.
