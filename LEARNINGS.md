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

## 2026-03-23 — Bootstrap: ruh-super-admin-fe — CI green (final)

**What happened:** Took 4 CI attempts to get ruh-super-admin-fe PR #139 green.
**Root cause chain:**
1. npm audit → no package-lock.json (Yarn project) → use yarn audit
2. TS 6.x baseUrl deprecation → add ignoreDeprecations:6.0
3. TS 6.x CSS imports → add src/css.d.ts stub
4. TS 6.x process/NodeJS.Timeout → @types/node needed → committed src/types/node-globals.d.ts minimal stub
5. package-lock.json accidentally committed → yarn --frozen-lockfile rejected it
6. eslint no-var rule hit declare var process in the stub → add eslint-disable-next-line

**Learning:** For TS 6.x Next.js projects: always commit node-globals.d.ts stub + css.d.ts + ignoreDeprecations:6.0 as part of bootstrap. Add @types/node to devDependencies so it goes into yarn.lock. Never commit package-lock.json in a Yarn project.

## 2026-03-23 — Heartbeat: sdr-management-mcp — pip-audit false positive + CVE bumps

**What happened:** pip-audit in MCP CI kept failing despite grep filter for ruh-campaign-mcp. 
**Root cause:** `uv export --no-editable` outputs `.` as the first non-comment line (self-reference to current project). pip-audit resolves `.` → installs local project → tries to audit `ruh-campaign-mcp` on PyPI → fails. The grep filter only excluded `^ruh-campaign-mcp`, not `^.$`.
**Fix applied:** Added `^\.$` to the grep exclusion pattern. Also bumped 6 fixable CVEs (black, cryptography, filelock, urllib3, pyjwt, python-multipart).
**Learning:** `uv export` always includes `.` as self-reference even with `--no-editable`. Always filter `^\.$` from requirements before pip-audit. This applies to all uv-managed projects.

## 2026-03-23 — Heartbeat: inbox-rotation — re-review PR #53

**What happened:** Team (AdityaRuh) pushed 3 commits adding 107 test methods after initial review flagged zero tests.
**Action:** Posted re-review acknowledging P1s resolved, noting remaining P2s (unbounded DNS cache, no body size limits, missing .env.example defaults).
**Learning:** Review feedback works — team delivered 107 tests from zero. Follow-up P2s tracked for next cycle.

## 2026-03-23 — Heartbeat: sdr-management-mcp — Security audit fix (PR #43)

**What happened:** pip-audit failed on PR #43 with 12 CVEs in 7 packages + private package skip warning.
**Root cause:** Transitive dependencies not bumped (authlib, black, cryptography, filelock, urllib3, pyjwt, python-multipart), plus starlette and diskcache pinned by upstream (mcp==1.26.0, no fix version respectively).
**Fix applied:** `uv lock --upgrade-package` for all fixable packages. Added `--ignore-vuln` for starlette (CVE-2025-62727) and diskcache (CVE-2025-69872) with documented reasons.
**Learning:** When pip-audit fails on a uv project, use `uv lock --upgrade-package <pkg>` to bump transitive deps. Always check if upstream constraints block the fix before adding ignore flags.

## 2026-03-23 — Heartbeat: inbox-rotation-service — Re-review PR #53

**What happened:** Team addressed P1 finding (zero tests) by adding 107 test methods across 10 files. Lint fixes also pushed.
**Root cause:** Initial PR had ~1200 lines of new code with no tests.
**Fix applied:** (Team) Added comprehensive test coverage. CI now all green (6/6 jobs).
**Learning:** P1 findings with concrete actionable items get addressed quickly. Team responded within same day.

## 2026-03-24 — Heartbeat: sdr-backend + sdr-management-mcp — Team PR reviews (SDR-1248)

**What happened:** Two companion PRs from JeetanshuDev for SDR-1248 (delayed reply check). Backend PR #447 has 72 tests but fails lint (ruff format). MCP PR #44 has zero tests and fails lint (undefined `Dict`) + security audit (11 CVEs in deps).
**Root cause:** (1) Developer didn't run `ruff format .` before pushing. (2) Used `Dict` instead of `dict` in MCP client. (3) MCP repo has stale dependencies with known CVEs. (4) No tests written for MCP side.
**Fix applied:** Posted Sentinel review comments on both PRs with clear P1/P2/P3 findings and fix instructions.
**Learning:** SDR-1248 spans two repos — always check companion PRs together. The MCP repo's dependency CVEs may be a systemic issue that needs a separate dependency bump PR.

## 2026-03-24 — Heartbeat: sdr-backend — Nightly regression failure (smoke)

**What happened:** Nightly regression smoke tests failed with `httpx.UnsupportedProtocol: Request URL is missing an 'http://' or 'https://' protocol`.
**Root cause:** `STAGING_URL` GitHub Actions variable is empty/not configured. Smoke tests try to hit an empty URL. This is the same known issue from HEARTBEAT.md — PR #446 was opened to skip smoke when STAGING_URL is not set.
**Fix applied:** PR #446 (by hiteshrapid) already addresses this — CI green, awaiting merge.
**Learning:** Smoke tests in nightly regression must gracefully skip when env vars are missing. PR #446 is the fix — needs to be merged to resolve recurring nightly failures.

## 2026-03-24 — Heartbeat: sdr-management-mcp — Nightly regression failure (smoke)

**What happened:** Nightly regression smoke tests failed with `pytest: error: unrecognized arguments: --timeout=30`.
**Root cause:** `pytest-timeout` not installed in the nightly regression workflow's dependency set. The `--extra dev` group doesn't include `pytest-timeout`. PR #43 (by hiteshrapid) was opened to fix this — CI green, awaiting merge.
**Fix applied:** PR #43 already addresses this — needs to be merged.
**Learning:** Nightly regression workflows must install the same test dependencies as CI. If smoke tests use `--timeout`, `pytest-timeout` must be in the dependency group.

## 2026-03-24 — Heartbeat: sdr-backend #447 + sdr-management-mcp #44 — Re-review after fixes

**What happened:** JeetanshuDev responded to Sentinel review within ~15 min, fixing all P1s on both companion PRs (lint formatting, undefined Dict, added tests).
**Root cause:** N/A — normal review-fix cycle.
**Fix applied:** Re-reviewed both PRs, confirmed all findings resolved, CI green on both. Posted re-review comments.
**Learning:** Fast turnaround from team on Sentinel reviews. The review→fix→re-review loop works well when findings are specific and actionable. Both SDR-1248 PRs now ready for Hitesh.

## 2026-03-24 — Heartbeat: ruh-super-admin-fe — CI fix (PR #139)

**What happened:** Stage 3 CI jobs (E2E, Lighthouse, Bundle Size) all failed with "Artifact not found for name: build-output". Build job completed successfully and `.next/` was produced, but `upload-artifact@v4` silently skipped it.
**Root cause:** `upload-artifact@v4` defaults `include-hidden-files` to `false`. Since `.next` starts with a dot, the entire directory was treated as hidden and skipped. No files uploaded = downstream jobs couldn't download.
**Fix applied:** Added `include-hidden-files: true` to both `ci.yml` and `nightly-regression.yml` build artifact upload steps.
**Learning:** Any Next.js CI pipeline using `upload-artifact@v4` to share `.next/` between jobs MUST set `include-hidden-files: true`. This is a silent failure — the upload step warns but doesn't error, so the build job passes while all consumers fail.

## 2026-03-24 — Heartbeat: ruh-super-admin-fe — Component test fixes

**What happened:** 7 new component test files (45+ tests) all failed in CI. Two root causes: (1) `@testing-library/dom` peer dependency missing, (2) test code bugs.
**Root cause 1:** `@testing-library/react@16` requires `@testing-library/dom` as peer dep but it wasn't in package.json or yarn.lock.
**Root cause 2:** `screen.getByAlt()` doesn't exist (correct: `screen.getByAltText()`). Also `userEvent.click()` on submit button in jsdom doesn't trigger form `onSubmit` — must use `fireEvent.submit(form)` for validation tests. Password toggle test used heuristic button finding instead of `screen.getByLabelText("Show password")`.
**Fix applied:** Added `@testing-library/dom@^10.4.1`, fixed `getByAlt→getByAltText`, used `fireEvent.submit` for form validation, used `getByLabelText` for toggle.
**Learning:** (1) Always verify peer dependencies are installed — CI uses `--frozen-lockfile` which won't auto-install peers. (2) In jsdom, `userEvent.click` on submit buttons is unreliable for form submission — use `fireEvent.submit`. (3) Use aria-labels to find buttons, not SVG heuristics.

---

## Frontend Testing Patterns (Next.js / TypeScript)

### CI Pipeline
- **Local E2E in PR CI** catches issues before merge — post-deploy E2E alone is too late (PR is already merged by then).
- **Build artifact reuse** — `next build` produces `.next/`, upload as artifact, download in e2e-local/lighthouse/bundle-size jobs. No rebuilding 3 times.
- **Concurrency control** is critical for frontend PRs — `cancel-in-progress: true` prevents stale runs piling up (frontend builds are expensive).
- **Next.js build cache** (`actions/cache` on `.next/cache`) dramatically speeds up incremental builds in CI.
- **`NEXT_TELEMETRY_DISABLED: 1`** — always set in CI to avoid telemetry noise.

### Component Testing
- Component tests fill the gap between unit tests (pure logic) and E2E (full browser). They render real React components with real DOM but without the full app.
- **100-500x faster than E2E** — a component test takes ~50-100ms vs ~5-30s for E2E.
- Test behavior, not implementation — use `screen.getByRole()`, `getByText()`, `getByLabelText()` over `getByTestId()`.
- `userEvent` over `fireEvent` — `userEvent` simulates real user behavior (focus, click, type), `fireEvent` is low-level synthetic.
- Mock at the boundary — mock API hooks (React Query/SWR) and context providers, not internal component methods.
- Mock `next/navigation` for any component that uses `useRouter`, `usePathname`, `useSearchParams`.

### Playwright / E2E
- `webServer` config in `playwright.config.ts` is required for local E2E — it starts `next start` automatically.
- `reuseExistingServer: !process.env.CI` — in CI always start fresh, locally reuse dev server.
- Playwright artifacts (screenshots, videos, traces) only on failure — saves CI time and storage.
- `data-testid` selectors are preferred but not always present in existing codebases — fallback to `getByRole`/`getByText`.

### Performance
- **Lighthouse budgets** catch silent perf regressions — set FCP < 2s, LCP < 3s, TTI < 5s as starting points.
- **Bundle size checks** — 500KB per-chunk limit catches accidental large imports (e.g., importing all of lodash).
- `wait-on` package is needed to wait for `next start` before Lighthouse runs — `npx wait-on http://localhost:3000 --timeout 30000`.

### Accessibility
- `@axe-core/cli` for quick nightly a11y checks — run against deployed or local build.
- Keep it nightly (not PR CI) to avoid slowing down the main pipeline — a11y violations rarely appear per-PR.
