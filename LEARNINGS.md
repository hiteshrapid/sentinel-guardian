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

## $(date +%Y-%m-%d) — Heartbeat: inbox-rotation-service PR #59 — CI fix: commit-lint + PR title

**What happened:** CI was failing on commit-lint after fixing commit history. Root cause: PR title `chore(ci): add SAST...` didn't match `PATTERN='^([A-Z]+-[0-9]+|\[QA Release\]|\[Prod Release\])'`. The `gh pr edit` command silently failed (exit 1) due to Projects Classic deprecation error — misleading because it printed GraphQL deprecation warning but still errored. 

**Root cause:** `gh pr edit --title` fails with exit code 1 when the repo has classic Projects attached (deprecation issue). The title mutation still needs to succeed via `gh api graphql` with `updatePullRequest`.

**Fix applied:** Used `gh api graphql` with `updatePullRequest` mutation using the PR's node_id to update the title. Force-pushed amended commit with canonical `commit-lint.yml` (validates all commits in range, not just PR title).

**Learning:** Never trust `gh pr edit` exit code alone when Projects Classic is present — always verify with `gh pr view --json title`. Use `gh api graphql updatePullRequest` as fallback when `gh pr edit` fails. Get node_id via `gh api repos/REPO/pulls/NUMBER --jq '.node_id'`.

## 2026-03-26 — Heartbeat: sdr-backend — Team PR reviews (#465, #466)

**What happened:** Reviewed 2 new team PRs. #465 (TT-240 slug config) all green. #466 (TT-241 race condition fix) has coverage drop to 99.99%.
**Root cause:** PR #466 added new code paths (atomic $set + "matched but not modified" branch) without full test coverage.
**Fix applied:** Posted P1 finding on #466 flagging coverage gap. Reviewed #465 with P3 nitpick only.
**Learning:** Atomic update patterns that add "no-op" branches (matched but not modified) commonly miss coverage. Flag early.

## 2026-03-26 — Heartbeat: smtp-imap-mcp — Bootstrap complete (PR #8 merged)

**What happened:** PR #8 merged to dev — full canonical 7-workflow pipeline with SAST/DAST/Bandit.
**Root cause:** N/A (bootstrap completion)
**Fix applied:** All 7 workflows deployed, Dockerfile hardened with non-root user, requests CVE fixed, pip-audit --no-dev export.
**Learning:** When adding SAST (Semgrep) to a repo, always check Dockerfile for missing USER directive — it's the #1 Semgrep finding. Also, pip-audit export should use --no-dev to avoid false positives from dev dependency CVEs.

## 2026-03-26 — Bootstrap: ruh-ai-admin-service — PR #33 complete

**What happened:** Upgraded existing bootstrap PR #33 to canonical 7-workflow pipeline. Added SAST/DAST/Bandit, commit-lint, jira-transition, ci-push. Fixed 3 Semgrep findings (Dockerfile USER, k8s securityContext), bumped requests 2.33.0 for CVE fix. Squashed 14 commits into 1 for commit-lint compliance.
**Root cause:** N/A (bootstrap)
**Fix applied:** Full canonical pipeline deployed, all security findings resolved.
**Learning:** gRPC + GKE repos will have k8s manifests that Semgrep flags for missing securityContext. Always check k8s manifests alongside Dockerfiles when adding SAST. Squash old commits when adding commit-lint to avoid retroactive failures.

## 2026-03-27 — Heartbeat: sdr-backend — Nightly regression failure (3 jobs) + 3 team PR reviews

**What happened:** Nightly regression failed on 3 jobs: Unit Tests (99.99% coverage), Security Audit (2 CVEs), E2E (BackendTestClient.get() AttributeError). Reviewed 3 new team PRs: inbox-rotation-service #64, sdr-backend #468, sdr-management-mcp #47.
**Root cause:**
  - Coverage: TT-241 `update()` method added "matched but not modified" path. The `not customer` → `return None` branch (line 1067) shipped to dev without a test.
  - Security: `requests==2.32.5` (CVE-2026-25645, fix: 2.33.0) + `pygments==2.19.2` (CVE-2026-4539).
  - E2E: `test_metrics.py` / `test_metrics_summary.py` call `backend_client.get()` but `BackendTestClient` has no `.get()` method.
**Fix applied:** Created TT-248. Spawned Claude Code fix agent on branch `fix/TT-248-nightly-regression-fixes`.
**Learning:** When TT-241-style "no-op path" patches merge to dev, the nightly immediately catches the coverage gap. The 99.99% signal is reliable and fast. `pygments` CVE with no fix → use `--ignore-vuln` in pip-audit rather than continue-on-error. Always verify BackendTestClient API surface when adding new e2e test files.

## 2026-03-27 — Fix: sdr-backend TT-248 nightly regression — PR #472

**What happened:** Fixed all 3 nightly regression failures. Coverage was actually already resolved by SDR-1248 commits that merged after the nightly ran — the coverage gap didn't need new tests, just confirmation. requests CVE bumped to 2.33.0. pygments CVE has no fix → --ignore-vuln pattern. BackendTestClient was missing .get()/.post() etc. convenience shorthands that test_metrics.py assumed existed.
**Root cause:** Nightly ran before SDR-1248 coverage fix landed. requests/pygments CVEs are real. BackendTestClient API surface mismatch — tests authored against a richer client interface than what was implemented.
**Fix applied:** PR #472 — requests bump + pygments ignore + BackendTestClient shorthands. Coverage already green.
**Learning:** Before writing new tests to fix coverage gaps, always check if recent commits to dev already address it — the nightly runs at 20:45 UTC and SDR-1248 merged at ~12:30 IST (07:00 UTC same day), so the nightly caught an in-flight gap. Always add HTTP method shorthands (get/post/put/patch/delete) to BackendTestClient when new e2e test files are created — tests naturally use them.

## 2026-03-27 — Heartbeat: sdr-backend — Lint fix on PR #472 + team PR reviews

**What happened:** PR #472 (Sentinel) had lint CI failure — `ruff format` needed on `tests/helpers/client.py`. Two unreviewed team PRs found: #460 (smoke fix) and #463 (QA release with ruff format failure).
**Root cause:** Format not run before push on #472. PR #463 team member didn't run ruff format on new test file.
**Fix applied:** Auto-fixed and force-pushed #472. Posted P2 review on #463 flagging ruff format issue. Posted P3-only review on #460.
**Learning:** Always run `uv run ruff format .` before amending/pushing. Format failures on test files are easy to miss since ruff check passes but format --check doesn't.

## 2026-03-30 — Heartbeat: sdr-backend — Fix nightly regression (TT-248)

**What happened:** Nightly regression failing 3 nights in a row. Unit test `test_calculate_business_days` fails on weekends (asserts `diff >= 5` calendar days, but weekends reduce the gap). Security audit flagged `cryptography` CVE-2026-34073 and `requests` CVE-2026-25645.
**Root cause:** Date-dependent test without frozen time + stale dependency pins.
**Fix applied:** Froze test to a known Monday (2026-01-05) using `unittest.mock.patch`. Bumped `cryptography>=46.0.6`. Pushed to existing PR #472.
**Learning:** Any test involving business day calculations MUST freeze the date. Never assert on relative calendar day counts without controlling the starting weekday.

## 2026-03-30 — Heartbeat: sdr-management-mcp — Standardize regression workflow name

**What happened:** `gh run list --workflow="Nightly Regression Suite"` returned "not found" for sdr-management-mcp because the workflow was named `Nightly Regression` (missing "Suite").
**Root cause:** Inconsistent naming during bootstrap — other repos used "Suite" suffix.
**Fix applied:** Renamed to `Nightly Regression Suite` in regression.yml on PR #47 branch.
**Learning:** Standardize workflow names across all repos. Add name consistency check to bootstrap checklist.

## 2026-03-30 — Heartbeat: sdr-backend — Lint failure after rebase (TT-248)

**What happened:** PR #472 CI failed on Lint + Type Check after rebase onto dev. `sdr_backend/api/emails.py` needed reformatting.
**Root cause:** Upstream code on dev had a formatting issue that wasn't caught before merge. Rebase pulled it into our branch.
**Fix applied:** `ruff format sdr_backend/api/emails.py`, amended commit, force-pushed.
**Learning:** Always run `ruff format --check .` locally after rebasing before pushing — upstream formatting issues will block our CI.

## 2026-03-30 — Heartbeat: ruh-ai-admin-service — Team PR review (#36)

**What happened:** New team PR from Rishabh — Redis TLS support (TT-257). Clean feature PR with config + client + test changes.
**Root cause:** N/A (feature PR, not a fix)
**Fix applied:** Reviewed and posted findings. 1 P2 finding: pre-existing security audit failure (cryptography + ecdsa CVEs on dev).
**Learning:** ruh-ai-admin-service also needs the cryptography bump to 46.0.6 — same CVE pattern as sdr-backend. Should batch these dependency bumps across repos.

## 2026-03-31 — Heartbeat: sdr-backend — Nightly regression partial fix

**What happened:** First nightly after PR #472 merge. Unit Tests, Security Audit, and Smoke Tests all passed (3 of 3 previous failures fixed). E2E Journey Tests still failing — 55 failed, 9 passed, 19 skipped.
**Root cause:** E2E tests hit staging API and get 405 Method Not Allowed + 404 Not Found. The staging deployment has API changes that broke E2E test contracts (sequence creation endpoint returns 405, campaign lookups return 404). This is a staging environment issue, not a test infrastructure problem.
**Fix applied:** None yet — needs investigation of which staging deploy changed the API contracts.
**Learning:** E2E tests against staging are inherently fragile when API contracts change. The E2E tests need updating to match current staging API, or staging needs redeployment with correct endpoints.
