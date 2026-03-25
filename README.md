# Sentinel Guardian ⚡🛡️

> Autonomous testing agent that achieves comprehensive test coverage on any codebase — then guards it forever.

Sentinel is an AI-powered testing agent built on [OpenClaw](https://openclaw.com). It operates in two modes: **Bootstrap** (build a complete test suite from scratch) and **Review** (continuously guard quality on every PR). Once a repo is bootstrapped, Sentinel shifts to review mode automatically — no manual switch needed.

## Proven Results

- **4,000+ tests** generated across production repositories
- **100% unit test coverage** achieved and enforced autonomously
- **71 targeted tests** written in a single PR review cycle to fill coverage gaps
- **11-layer testing pyramid** — unit → component → integration → contract → security → resilience → smoke → API E2E → browser E2E → regression
- **5 stack contexts** — FastAPI/Beanie, FastAPI/SQLAlchemy, Flask, Django, Next.js/TypeScript
- **Frontend-aware** — Lighthouse performance budgets, bundle size checks, component tests, local E2E in PR CI
- **7 canonical CI workflows** bootstrapped per repo — see `github-pipeline` skill for the full chain

## Two Modes of Operation

### 🔨 Mode 1: Bootstrap (Offensive)

Build the entire quality system from scratch on a new or under-tested repo.

```bash
/scan https://github.com/your-org/your-repo
```

**What Sentinel builds:**
- Complete test suites across all applicable layers
- CI workflow (`ci.yml`) with lint → unit → integration → security → contract pipeline
- Post-deploy workflow (`post-deploy.yml`) — smoke + E2E against live environment
- Nightly regression workflow (`regression.yml`) with Slack failure alerts
- 100% unit coverage enforced via `--cov-fail-under=100`

**For backend repos:**
- Unit → Integration → Contract → Security → Resilience pipeline
- Service containers (MongoDB, Redis) for integration tests
- 100% unit coverage enforced

**For frontend repos (Next.js):**
- Lint + Typecheck → Unit + Component → Build → E2E local + Lighthouse + Bundle size
- Component tests for forms, modals, tables, conditional rendering
- Playwright E2E against local `next start` (webServer config)
- Lighthouse performance budgets (`lighthouse-budget.json`)
- Bundle size regression checks (500KB per-chunk limit)
- Accessibility audits via axe-core (nightly)

**Output:** One PR with everything. Clean, tested, ready to merge.

### 🛡️ Mode 2: Review (Defensive)

Guard quality on repos that are already bootstrapped. Runs automatically during heartbeats.

**What Sentinel checks on every team PR:**

| Category | What's Checked |
|----------|---------------|
| **Coverage** | Does the PR drop unit coverage? New files without tests? New functions untested? |
| **Test Quality** | Meaningful assertions? Mocks targeting real methods? Tests isolated? |
| **Breaking Changes** | API signature changes without contract test updates? Schema changes? |
| **Security** | Unauthed endpoints? Known CVEs in new deps? Hardcoded secrets? Injection vectors? |
| **Patterns** | Following repo conventions? Unjustified `noqa`/`pragma: no cover`? Dead code? |

**Review output** uses a clear severity framework:

```
🛡️ Sentinel Review — PR #53

Blocking (must fix before merge):
- 🔴 P1: Zero tests for ~1,181 lines of new code
- 🔴 P1: SuppressionListService uses sync MongoDB in async codebase

Should fix:
- 🟡 P2: email_validator.py makes unbounded DNS lookups — cache grows forever
- 🟡 P2: NDR regex parsing has no input size limit (ReDoS risk)

Observations:
- 🟢 P3: Good DRY improvement consolidating bounce handlers
```

**Rules:** Sentinel flags but never auto-fixes team PRs. Never approves or merges — that's always the team's call.

## The Testing Pyramid

| Layer | What It Tests | When |
|-------|--------------|------|
| **Unit** | Business logic in isolation, 100% coverage mandatory | Every PR |
| **Component** | React components rendered with real DOM, user interactions, state changes | Every PR (frontend) |
| **Integration** | HTTP → service → database flow with real infra | Every PR |
| **Contract** | OpenAPI/schema regression lock | Every PR |
| **Security** | Auth boundaries, injection, headers, dependency audit | Every PR |
| **Resilience** | Timeouts, connection errors, 5xx recovery, partial failures | Backend services |
| **Smoke** | Fast post-deploy health checks (<30s) | After deploy |
| **API E2E** | Multi-step API journey tests | After deploy |
| **Browser E2E** | Playwright UI flows with screenshots | After deploy |
| **Regression** | Nightly full-suite run with failure triage | Scheduled |

## CI Workflow Architecture

Every bootstrapped repo gets seven canonical workflows (see `github-pipeline` skill). The three core ones:

```
ci.yml (PR + push)              post-deploy.yml (after deploy)     regression.yml (nightly)
─────────────────               ──────────────────────────          ─────────────────────────
lint-typecheck ──┐              Deploy succeeds                    Cron schedule
  ├── unit       │              │                                  │
  ├── integration│              ├── smoke (health + endpoints)     ├── full offline suite
  ├── security   │→ contract    ├── e2e (journeys)                 ├── SAST (Semgrep)
  ├── sec-audit  │              └── dast (OWASP ZAP)               ├── smoke + e2e vs live
  └── sast ──────┘                                                 ├── dast (OWASP ZAP)
                                                                   └── Slack alert on failure
```

**Job dependency graph:**
```
lint-typecheck
      │
  ┌───┼───────────┬───────────────┬───────────────┐
  ▼   ▼           ▼               ▼               ▼
unit  integration  security-tests  security-audit  sast (Semgrep)
  │   │
  ▼   ▼
contract (needs: [unit, integration])
```

### Frontend CI Architecture (Next.js / TypeScript)

Frontend repos get a different, broader pipeline — no integration/contract/resilience, but adds build verification, local E2E, Lighthouse performance audits, and bundle size checks.

```
ci.yml (PR + push)              post-deploy.yml (after deploy)     nightly-regression.yml (2 AM IST)
─────────────────               ──────────────────────────          ────────────────────────────────
lint ─────┐                     Deploy succeeds                    Cron schedule
           ├─ unit+component    │                                  │
typecheck ─┤                    ├── smoke (curl health)            ├── unit+component
           └─ build ──┐        └── e2e (Playwright vs deployed)   ├── build
              ├─ e2e-local                                         ├── e2e-local (vs local build)
              ├─ lighthouse                                        ├── e2e-deployed (vs live dev)
              └─ bundle-size                                       ├── lighthouse (vs live dev)
security-audit (parallel)                                          └── accessibility (axe-core)
```

**Frontend-specific jobs (not in backend):**
- **build** — `next build` producing artifact reused by downstream jobs
- **e2e-local** — Playwright tests against `next start` on localhost (catches issues before merge)
- **lighthouse** — performance budgets (FCP, LCP, TTI, bundle sizes)
- **bundle-size** — fails if any JS chunk exceeds 500KB
- **component tests** — React components rendered with Testing Library (runs alongside unit tests)
- **accessibility** — axe-core audit (nightly only)

**Key difference from backend:** E2E runs locally in PR CI, not just post-deploy. This ensures tests actually catch issues before merge, not after.

## Supported Stacks

| Stack | Auto-detected via |
|-------|-------------------|
| FastAPI + MongoDB/Beanie | `from fastapi` + `beanie`/`motor` imports |
| FastAPI + PostgreSQL/SQLAlchemy | `from fastapi` + `sqlalchemy` imports |
| Flask + SQLAlchemy | `from flask` imports |
| Django + Django ORM | `from django` imports |
| Next.js + TypeScript | `package.json` with `next` + `next.config.ts`/`mjs` |

New stacks? Sentinel analyzes the repo and creates a context automatically.

## Quick Start

### Commands

```bash
# Bootstrap a new repo
/scan /path/to/your/repo

# Push unit coverage to 100%
/cover

# Fix a CI failure
/fix-ci

# Generate E2E tests
/e2e

# Review a specific PR
/review-pr 53

# Run security analysis
/secure
```

### Installation

Sentinel runs as an [OpenClaw](https://openclaw.com) workspace agent.

1. Install OpenClaw
2. Clone this repo into your OpenClaw workspace directory
3. Copy `USER.md.template` to `USER.md` and fill in your details
4. Configure the agent in your OpenClaw config

## Agent Architecture

Sentinel spawns specialized sub-agents for each testing layer:

| Agent | Role |
|-------|------|
| **Analyzer** | Detect stack, map CI, produce phased test plan |
| **Coverage** | Push unit coverage to 100% with correct file placement |
| **Integration** | Build request → service → DB flow tests |
| **Contract** | Lock API/schema contracts |
| **Security** | Auth boundaries, injection, dependency scanning |
| **Resilience** | Timeouts, connection errors, graceful degradation |
| **Smoke** | Post-deploy health checks |
| **E2E** | Browser-critical Playwright flows |
| **Regression** | Nightly CI wiring + failure triage |
| **Review** | Post-write quality gate (dedup, mock audit, DB safety) |
| **Component** | Frontend component tests (React Testing Library + Vitest) |
| **PR Review** | Team PR guardian (coverage, security, patterns) |
| **Verifier** | Final pass — validate everything is green |

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full dependency graph.

## Key Design Decisions

- **100% unit coverage is mandatory** — CI enforces `--cov-fail-under=100`, never lowered
- **One open Sentinel PR per repo** — no PR spam, fixes go to existing branches
- **Flag, don't auto-fix** team PRs — Sentinel reviews and reports, humans decide
- **Never merge or auto-merge** — opening PRs is Sentinel's lane, merging is the team's
- **External services always mocked** — centralized `conftest.py` fixtures, never per-file hacks
- **Bootstrap is one-time, review is forever** — automatic mode transition after merge
- **Learnings persist** — every fix teaches Sentinel patterns applied to future repos

## Learnings System

Sentinel maintains a living knowledge base:
- **LEARNINGS.md** — accumulated patterns, gotchas, and fixes from every repo
- **memory/** — dated session logs for audit trail
- **Contexts** — stack-specific testing patterns that improve over time

Examples of learned patterns:
- Private packages fail `pip-audit --strict` (not a vulnerability — needs carve-out)
- Beanie `!= True` must use `# noqa: E712` (ORM overloads `!=` for queries)
- `db_manager` singleton mutations break test isolation without save/restore
- Production DB name must never be the test default

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to add skills, contexts, and agents.

## License

MIT — see [LICENSE](LICENSE)

---

Built by [Hitesh Goyal](https://github.com/iamhiteshgoyal) — [Ruh AI](https://ruh.ai).

*"Great testing, like great energy, should flow freely to every codebase."*
