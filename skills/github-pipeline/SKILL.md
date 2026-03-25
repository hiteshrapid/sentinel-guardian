---
name: github-pipeline
description: >
  Sets up a complete GitHub Actions CI/CD pipeline for TypeScript, Python, or
  Next.js projects. Use this skill whenever a user wants to configure GitHub
  Actions workflows, set up CI/CD pipelines, add automated testing pipelines,
  configure deployment workflows to GKE/Kubernetes, set up Jira ticket
  auto-transitions, add nightly regression testing, or asks about any of the
  workflow files: ci.yml, ci-push.yml, commit-lint.yml, build-deploy.yml,
  post-deploy.yml, jira-transition.yml, or regression.yml. Also trigger when
  the user mentions "GitHub pipeline", "workflow setup", "CI/CD for Node",
  "CI/CD for Python", "CI/CD for Next.js", or "automate deployments".
---

# GitHub Actions CI/CD Pipeline Setup

This skill sets up a production-grade GitHub Actions pipeline supporting **TypeScript**, **Python**, and **Next.js** projects, with:
- PR and merge CI checks (lint, type-check, unit, integration, contract, security, SAST)
- Docker build + GKE deploy (with manual approval gates for qa/prod)
- Post-deploy smoke → E2E → DAST tests
- Jira ticket auto-transitions
- Nightly regression suite with Slack alerts

## Workflow Chain

```
PR opened
    │
    ▼
[CI] ──────────────── PR checks only, never deploys
    │
    │  (PR merged)
    ▼
[CI (Merge)] ────────── Same checks, no commit-lint
    │ success
    ▼
[Build and Deploy] ─────── Manual approval required for qa/prod
    │ success
    ▼
[Post-Deploy Tests] ─────── Smoke → E2E → DAST against live URL
    │ success
    ▼
[Jira Transition] ──────── Auto-moves ticket to correct status
```

Additionally, a **Nightly Regression** workflow runs at 2 AM UTC against `dev`.

---

## Step 1: Collect Configuration

Before generating any files, ask the user for:

1. **Project type**: TypeScript/Node.js, Python, or Next.js
2. **Jira project keys** (e.g. `RP`, `TT`, `SDR`, `ES`) — used in commit-lint and jira-transition regex
3. **Jira transition status names** for each branch:
   - `dev` deploys → e.g. `Ready to Deploy - QA`
   - `qa` deploys → e.g. `IN QA`
   - `main` deploys → e.g. `RELEASED TO PROD`
4. **Build/deploy mechanism**: Are they using the `ruh-ai/reusable-workflows-and-charts` reusable workflows, or do they need custom Docker build + kubectl steps?
5. **Slack alerts**: Do they want nightly regression Slack notifications? (requires `SLACK_BOT_TOKEN` + `SLACK_ALERTS_CHANNEL` secrets)
6. **Package manager** (Node-based projects only): yarn (default), npm, or pnpm

If the user says "use defaults" or provides partial info, use the values from the reference files and note which ones need updating.

---

## Step 2: Generate Workflow Files

The `ci.yml` and `ci-push.yml` files differ by project type. Read the correct reference for the user's project. All other files are shared across project types.

### CI Reference by Project Type

| Project Type | `ci.yml` | `ci-push.yml` | `regression.yml` |
|---|---|---|---|
| TypeScript / Node.js | `references/ci.md` | `references/ci-push.md` | `references/regression.md` |
| Next.js | `references/ci-nextjs.md` | `references/ci-push-nextjs.md` | `references/regression-nextjs.md` |
| Python | `references/ci-python.md` | `references/ci-push-python.md` | `references/regression-python.md` |

### Shared Workflow Files (same for all project types)

| File | Reference |
|------|-----------|
| `commit-lint.yml` | `references/commit-lint.md` |
| `build-deploy.yml` | `references/build-deploy.md` |
| `jira-transition.yml` | `references/jira-transition.md` |

### Post-Deploy Reference by Project Type

| Project Type | Reference |
|---|---|
| TypeScript / Node.js | `references/post-deploy.md` |
| Next.js | `references/post-deploy-nextjs.md` |
| Python | `references/post-deploy-python.md` |

### Regression Reference by Project Type

| Project Type | Reference |
|---|---|
| TypeScript / Node.js | `references/regression.md` |
| Next.js | `references/regression-nextjs.md` |
| Python | `references/regression-python.md` |

### Apply Customizations

- Replace Jira project key regex in `commit-lint.yml` and `jira-transition.yml`
- Replace Jira transition names in `jira-transition.yml`
- If custom build/deploy: replace the `uses: ruh-ai/reusable-workflows...` blocks in `build-deploy.yml`
- If npm/pnpm (Node projects): replace all `yarn` commands accordingly
- For Python: `regression.yml` uses `pytest` — see `references/ci-python.md` for the test command patterns

---

## Step 3: Output Files

Write all 7 files to `.github/workflows/` and present them to the user.

---

## Step 4: Provide Setup Checklist

After presenting the files, give the user this checklist:

### GitHub Repository Variables (Settings → Secrets and variables → Actions → Variables tab)
| Variable | Example |
|----------|---------|
| `DEV_URL` | `https://app-dev.yourdomain.com` |
| `QA_URL` | `https://app-qa.yourdomain.com` |
| `PROD_URL` | `https://app.yourdomain.com` |

### GitHub Repository Secrets (Settings → Secrets tab)
| Secret | Description |
|--------|-------------|
| `DEV_API_KEY` | API key for dev environment |
| `QA_API_KEY` | API key for qa environment |
| `PROD_API_KEY` | API key for prod environment |
| `JIRA_BASE_URL` | e.g. `https://yourcompany.atlassian.net` |
| `JIRA_EMAIL` | CI bot email |
| `JIRA_API_TOKEN` | From id.atlassian.com → Security → API tokens |
| `GCP_PROJECT_ID` | Google Cloud project ID |
| `GCP_SA_KEY` | GCP service account JSON key |
| `GKE_CLUSTER` | GKE cluster name |
| `GKE_ZONE` | GKE cluster zone/region |
| `DOCKER_REGISTRY` | e.g. `gcr.io/your-project` |
| `SLACK_BOT_TOKEN` | (if nightly Slack alerts enabled) |
| `SLACK_ALERTS_CHANNEL` | Slack channel ID (if enabled) |

### GitHub Environments (Settings → Environments → New environment)
- **`qa`**: Add required reviewers, restrict to `qa` branch
- **`prod`**: Add required reviewers, restrict to `main` branch
- `dev` does NOT need an environment (deploys automatically)

### Branch Protection Rules (Settings → Branches → Add rule)
Apply to `dev`, `qa`, `main`:
- Require status checks: `Lint + Type Check`, `Unit Tests`, `Integration Tests`, `Contract Tests`, `SAST (Semgrep)`
- Require branches to be up to date ✅
- Require PR reviews (at least 1 approver) ✅
- No direct pushes ✅

### Project-Type-Specific Setup

#### TypeScript / Node.js — `package.json` scripts required:
```json
{
  "scripts": {
    "test:unit:coverage": "jest --testPathPattern=tests/unit --coverage",
    "test:integration":   "jest --testPathPattern=tests/integration",
    "test:contract":      "jest --testPathPattern=tests/contract",
    "test:security":      "jest --testPathPattern=tests/security",
    "test:smoke":         "jest --testPathPattern=tests/smoke",
    "test:e2e":           "jest --testPathPattern=tests/e2e",
    "security:audit":     "yarn audit --level moderate"
  }
}
```

#### Next.js — additional scripts required:
```json
{
  "scripts": {
    "build": "next build",
    "test:unit:coverage": "jest --testPathPattern=tests/unit --coverage",
    "test:integration":   "jest --testPathPattern=tests/integration",
    "test:e2e":           "playwright test",
    "test:smoke":         "jest --testPathPattern=tests/smoke",
    "security:audit":     "yarn audit --level moderate"
  }
}
```


#### Next.js — additional setup required:
```json
{
  "scripts": {
    "dev": "next dev --turbopack",
    "build": "next build",
    "start": "next start",
    "lint": "next lint",
    "typecheck": "tsc --noEmit",
    "test": "vitest run",
    "test:coverage": "vitest run --coverage",
    "test:e2e": "npx playwright test"
  }
}
```

**vitest.config.ts** — include both unit and component test directories:
```typescript
export default defineConfig({
  test: {
    include: ['tests/unit/**/*.test.ts', 'tests/components/**/*.test.tsx'],
    environment: 'jsdom',
    setupFiles: ['./tests/setup.ts'],
  },
});
```

**playwright.config.ts** — must include webServer block for local E2E:
```typescript
export default defineConfig({
  webServer: {
    command: 'yarn start',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
    timeout: 30_000,
  },
});
```

**.next/cache caching** — CI build job uses actions/cache for .next/cache. Build artifact upload must use `include-hidden-files: true`.

#### Python — `pyproject.toml` / `requirements` setup:
- `pytest` with `pytest-cov` for unit/integration tests
- `bandit` for security scanning
- `ruff` or `flake8` for linting
- `mypy` for type checking
- See `references/ci-python.md` for the exact commands used in the workflows

### `.env.example`
Must include all required vars with safe test defaults:
```
DB_SSL=false
DB_SSL_REJECT_UNAUTHORIZED=false
RATE_LIMIT_MAX=10000
RATE_LIMIT_WINDOW_MS=60000
```

---

## Important: Workflow Name Coupling

These workflows chain by listening to each other's `name:` field. If a workflow is renamed, update all references:

| File | `name:` field | Referenced in |
|------|--------------|---------------|
| `ci-push.yml` | `CI (Merge)` | `build-deploy.yml` → `workflows: ["CI (Merge)"]` |
| `build-deploy.yml` | `Build and Deploy` | `post-deploy.yml` → `workflows: ["Build and Deploy"]` |
| `post-deploy.yml` | `Post-Deploy Tests` | `jira-transition.yml` → `workflows: ["Post-Deploy Tests"]` |
