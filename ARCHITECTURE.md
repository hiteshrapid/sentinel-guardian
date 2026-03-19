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
│       └── nextjs-prisma.md
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

### The Testing Pyramid
Sentinel implements a 9-layer testing pyramid, executed in order:
1. Setup (bootstrap infrastructure)
2. Unit tests (business logic, mocked I/O)
3. Integration tests (real DB via Testcontainers)
4. Contract tests (OpenAPI schema lock)
5. Security tests (auth, injection, headers)
6. Smoke tests (post-deploy health)
7. API E2E tests (multi-step workflows)
8. Browser E2E tests (Playwright UI flows)
9. Regression tests (nightly scheduled runs)

### Heartbeat
Sentinel monitors connected repos autonomously. Every heartbeat it checks PRs, CI status, nightly regressions, and coverage. If something needs fixing, it acts. After every action, it writes what it learned to LEARNINGS.md.
