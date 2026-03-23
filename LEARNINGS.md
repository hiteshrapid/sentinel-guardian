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
