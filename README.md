# Sentinel Guardian ⚡🛡️

> Autonomous testing agent that achieves comprehensive test coverage on any codebase — then guards it forever.

Sentinel is an AI-powered testing agent built on [OpenClaw](https://openclaw.com). It operates in two modes: **Bootstrap** (build a complete test suite from scratch) and **Review** (continuously guard quality on every PR). Once a repo is bootstrapped, Sentinel shifts to review mode automatically — no manual switch needed.

## Proven Results

- **4,000+ tests** generated across production repositories
- **100% unit test coverage** achieved and enforced autonomously
- **71 targeted tests** written in a single PR review cycle to fill coverage gaps
- **9-layer testing pyramid** — unit → integration → contract → security → resilience → smoke → API E2E → browser E2E → regression
- **5 stack contexts** — FastAPI/Beanie, FastAPI/SQLAlchemy, Flask, Django, Next.js/Prisma
- **3 canonical CI workflows** bootstrapped per repo — `ci.yml`, `post-deploy.yml`, `regression.yml`

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
| **Integration** | HTTP → service → database flow with real infra | Every PR |
| **Contract** | OpenAPI/schema regression lock | Every PR |
| **Security** | Auth boundaries, injection, headers, dependency audit | Every PR |
| **Resilience** | Timeouts, connection errors, 5xx recovery, partial failures | Backend services |
| **Smoke** | Fast post-deploy health checks (<30s) | After deploy |
| **API E2E** | Multi-step API journey tests | After deploy |
| **Browser E2E** | Playwright UI flows with screenshots | After deploy |
| **Regression** | Nightly full-suite run with failure triage | Scheduled |

## CI Workflow Architecture

Every bootstrapped repo gets three workflows:

```
ci.yml (PR + push)              post-deploy.yml (after deploy)     regression.yml (nightly)
─────────────────               ──────────────────────────          ─────────────────────────
lint-typecheck ──┐              Deploy succeeds                    Cron schedule
  ├── unit       │              │                                  │
  ├── integration│              ├── smoke (health + endpoints)     ├── full offline suite
  ├── security   │              └── e2e (journeys)                 ├── smoke vs live
  └── contract ──┘                                                 ├── e2e vs live
                                                                   └── Slack alert on failure
security-audit (parallel, no deps)
```

**Job dependency graph:**
```
lint-typecheck          security-audit
      │                 (independent)
  ┌───┼───────────┐
  ▼   ▼           ▼
unit  integration  security-tests
  │   │
  ▼   ▼
contract (needs: [unit, integration])
```

## Supported Stacks

| Stack | Auto-detected via |
|-------|-------------------|
| FastAPI + MongoDB/Beanie | `from fastapi` + `beanie`/`motor` imports |
| FastAPI + PostgreSQL/SQLAlchemy | `from fastapi` + `sqlalchemy` imports |
| Flask + SQLAlchemy | `from flask` imports |
| Django + Django ORM | `from django` imports |
| Next.js + Prisma | `package.json` with `next` + `prisma` |

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

Built by [Hitesh Goyal](https://github.com/iamhiteshgoyal) — founder of [Ruh AI](https://ruh.ai).

*"Great testing, like great energy, should flow freely to every codebase."*
