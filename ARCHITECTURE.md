# Architecture

Sentinel is an autonomous testing agent built as an OpenClaw workspace. It uses a layered architecture: skills define what to do, agents execute the work, and contexts adapt to the target stack.

## How It Works

```
User: /scan /path/to/repo
         │
         ▼
    ┌─────────────┐
    │  Analyzer    │  Detects stack, reads code, produces test plan
    │  Agent       │
    └──────┬──────┘
           │ spawns parallel agents
           ▼
    ┌──────────────────────────────────────────┐
    │  Coverage  │ Integration │ Security │ ... │
    │  Agent     │ Agent       │ Agent    │     │
    └──────┬─────┴──────┬──────┴────┬─────┴─────┘
           │            │           │
           ▼            ▼           ▼
    ┌─────────┐  ┌───────────┐  ┌──────────┐
    │ unit-   │  │integration│  │ security │
    │ tests   │  │ -tests    │  │ -tests   │
    │ SKILL   │  │ SKILL     │  │ SKILL    │
    └────┬────┘  └─────┬─────┘  └────┬─────┘
         │             │              │
         ▼             ▼              ▼
    ┌─────────────────────────────────────────┐
    │         Stack Context                    │
    │  (fastapi-beanie / nextjs-prisma / ...)  │
    └──────────────────────────────────────────┘
```

## Directory Layout

```
sentinel-guardian/
├── SOUL.md              Agent personality, rules, principles
├── IDENTITY.md          Name, vibe, emoji
├── HEARTBEAT.md         Autonomous monitoring checklist
├── BOOTSTRAP.md         New repo onboarding flow
├── AGENTS.md            Sub-agent portfolio and repo tracker
├── TOOLS.md             Tool configuration
├── LEARNINGS.md         Battle-tested patterns from deployments
│
├── skills/              Testing skills (the knowledge base)
│   ├── test-setup/      Bootstrap test infrastructure
│   ├── unit-tests/      Unit test patterns
│   ├── component-tests/ Frontend React component tests (Vitest + Testing Library)
│   ├── integration-tests/  Integration with real DB
│   ├── contract-tests/  OpenAPI schema locking
│   ├── security-tests/  Auth, injection, headers
│   ├── smoke-tests/     Post-deploy health checks
│   ├── e2e-api-tests/   Multi-step API workflows
│   ├── e2e-browser-tests/  Playwright browser flows
│   ├── regression-tests/   Nightly scheduled runs
│   └── contexts/        Stack-specific patterns
│       ├── fastapi-beanie.md
│       ├── fastapi-sqlalchemy.md
│       ├── flask-sqlalchemy.md
│       ├── django-orm.md
│       └── nextjs-typescript.md
│
├── agents/              Sub-agent definitions
│   ├── analyzer.md      Stack detection + test planning
│   ├── coverage-agent.md    Write unit tests to fill gaps
│   ├── integration-agent.md Real DB integration tests
│   ├── contract-agent.md    Schema locking
│   ├── security-agent.md    Security boundary tests
│   ├── smoke-agent.md       Post-deploy checks
│   ├── e2e-agent.md         API + browser E2E
│   ├── resilience-agent.md  Failure handling tests
│   ├── regression-agent.md  Nightly CI setup
│   ├── ci-fix-agent.md      Diagnose + fix CI failures
│   └── verifier.md          Final pass before merge
│
├── commands/            Slash commands
│   ├── scan.md          /scan — analyze repo, plan tests
│   ├── cover.md         /cover — push to 100% coverage
│   ├── fix-ci.md        /fix-ci — diagnose CI failures
│   ├── e2e.md           /e2e — generate E2E tests
│   ├── report.md        /report — coverage summary
│   ├── sentinel-deploy.md   Full pyramid deployment
│   └── sentinel-watch.md    PR monitoring
│
└── templates/           Starter files for new repos
    ├── conftest-sqlalchemy.py
    ├── conftest-beanie.py
    ├── conftest-playwright.py
    └── ci-workflows/
        ├── ci.yml.template
        ├── e2e.yml.template
        └── regression.yml.template
```

## Key Concepts

### Skills vs Agents
- **Skills** are knowledge documents — they describe HOW to write a type of test
- **Agents** are executors — they READ a skill and DO the work
- Each agent loads the relevant skill + stack context before writing code

### Stack Contexts
Skills are generic. Contexts make them specific. When Sentinel encounters a FastAPI + MongoDB repo, it loads `contexts/fastapi-beanie.md` which tells it the auth pattern, DB setup, package manager, and code examples for that stack.

### Stack Auto-Detection (Frontend vs Backend)

Sentinel auto-detects the stack before applying templates:

| Signal | Stack | CI Template |
|--------|-------|-------------|
| `package.json` + `next` | Next.js (frontend) | lint, typecheck, unit+component, build, e2e-local, lighthouse, bundle-size |
| `pyproject.toml` / `requirements.txt` | Python (backend) | lint-typecheck, unit, integration, security, resilience, contract |

**Frontend-only jobs:** build (artifact), e2e-local (Playwright vs localhost), lighthouse (performance), bundle-size, component tests, accessibility (nightly)

**Backend-only jobs:** integration (service containers), resilience, contract (OpenAPI schema)

### The Testing Pyramid
Sentinel implements an 11-layer testing pyramid, executed in order:
1. Setup (bootstrap infrastructure)
2. Unit tests (business logic, mocked I/O — 100% coverage mandatory)
3. Component tests (frontend only — React components with real DOM via Vitest + Testing Library — 100% coverage mandatory)
4. Integration tests (real DB via Testcontainers, backend only)
5. Contract tests (OpenAPI schema lock, backend only)
6. Security tests — runtime (auth, injection, headers) + static (SAST via Semgrep/Bandit, dependency audit via pip-audit/yarn-audit)
7. Resilience tests (conditional — backend services with external deps only)
8. Smoke tests (post-deploy health)
9. E2E tests (API workflows + Playwright browser flows)
10. Regression tests (nightly scheduled runs)
11. Post-write review (mandatory quality gate before commit)

### Heartbeat
Sentinel monitors connected repos autonomously. Every heartbeat it checks PRs, CI status, nightly regressions, and coverage. If something needs fixing, it acts. After every action, it writes what it learned to LEARNINGS.md.
