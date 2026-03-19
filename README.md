# Sentinel Guardian

> Autonomous testing agent that achieves comprehensive test coverage on any codebase.

Sentinel detects your tech stack, generates a test plan, spawns specialized agents, and delivers a complete test suite — from unit tests to browser E2E. Built on [OpenClaw](https://openclaw.com).

## Proven Results

- **4,000+ tests** generated across 3 production repositories
- **100% unit test coverage** achieved autonomously
- **9-layer testing pyramid** — unit, integration, contract, security, smoke, API E2E, browser E2E, resilience, regression
- **5 stack contexts** — FastAPI/Beanie, FastAPI/SQLAlchemy, Flask, Django, Next.js/Prisma

## Quick Start

```bash
# Deploy Sentinel on your repo
/scan /path/to/your/repo

# Push coverage to 100%
/cover

# Fix a CI failure
/fix-ci

# Generate E2E tests
/e2e
```

## What Sentinel Does

1. **Detects** your stack (framework, DB, auth, package manager)
2. **Plans** which test layers are needed
3. **Spawns** parallel agents for each layer
4. **Writes** tests in the correct files with correct patterns
5. **Verifies** all gates pass before reporting complete
6. **Monitors** PRs, CI, and nightly regressions via heartbeat
7. **Learns** from every deployment and applies patterns to future repos

## The Testing Pyramid

| Layer | Skill | What It Tests |
|---|---|---|
| Setup | `test-setup` | Bootstrap infrastructure for all layers |
| Unit | `unit-tests` | Business logic in isolation |
| Integration | `integration-tests` | HTTP + real DB via Testcontainers |
| Contract | `contract-tests` | OpenAPI schema regression |
| Security | `security-tests` | Auth, injection, headers, audit |
| Smoke | `smoke-tests` | Post-deploy health checks |
| API E2E | `e2e-api-tests` | Multi-step API workflows |
| Browser E2E | `e2e-browser-tests` | Playwright UI flows |
| Regression | `regression-tests` | Nightly scheduled full suite |

## Supported Stacks

| Stack | Context |
|---|---|
| FastAPI + MongoDB/Beanie | `contexts/fastapi-beanie.md` |
| FastAPI + PostgreSQL/SQLAlchemy | `contexts/fastapi-sqlalchemy.md` |
| Flask + SQLAlchemy | `contexts/flask-sqlalchemy.md` |
| Django + Django ORM | `contexts/django-orm.md` |
| Next.js + Prisma | `contexts/nextjs-prisma.md` |

New stacks? Sentinel analyzes the repo and creates a context automatically.

## Installation

Sentinel runs as an OpenClaw workspace agent.

1. Install [OpenClaw](https://openclaw.com)
2. Clone this repo into your OpenClaw workspace directory
3. Copy `USER.md.template` to `USER.md` and fill in your details
4. Configure the agent in `openclaw.json`

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for how the pieces fit together.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to add skills, contexts, and agents.

## License

MIT — see [LICENSE](LICENSE)

---

Built by [Hitesh Goyal](https://github.com/iamhiteshgoyal) — founder of Ruh AI.

*"Great testing, like great energy, should flow freely to every codebase."*
