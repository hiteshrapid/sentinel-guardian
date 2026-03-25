# ci-push.yml — Merge Checks

```yaml
name: CI (Merge)

# Workflow 1b — Runs only on push (merge) to dev/qa/main.
# Triggers "Build and Deploy" workflow via workflow_run.
# Commit messages were already validated during PR — skipped here.
#
# ── Jobs ──────────────────────────────────────────────────────────────────────
# lint-typecheck → unit          ┐
#               → integration  ┤→ contract
#               → security-tests
#               → security-audit
#               → sast

on:
  push:
    branches: [dev, qa, main]
  workflow_dispatch:

# Queue push runs — do not cancel mid-deploy.
concurrency:
  group: ci-push-${{ github.ref }}
  cancel-in-progress: false

env:
  FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: "true"

jobs:
  lint-typecheck:
    name: Lint + Type Check
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: "20", cache: "yarn" }
      - run: yarn install --frozen-lockfile
      - run: npx tsc --noEmit

  unit:
    name: Unit Tests
    runs-on: ubuntu-latest
    timeout-minutes: 15
    needs: lint-typecheck
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: "20", cache: "yarn" }
      - run: yarn install --frozen-lockfile
      - run: cp .env.example .env
      - run: yarn test:unit:coverage
      - name: Upload coverage report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: coverage-report
          path: coverage/

  integration:
    name: Integration Tests
    runs-on: ubuntu-latest
    timeout-minutes: 20
    needs: lint-typecheck
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: "20", cache: "yarn" }
      - run: yarn install --frozen-lockfile
      - run: cp .env.example .env
      - run: yarn test:integration
        env:
          TESTCONTAINERS_RYUK_DISABLED: "true"

  contract:
    name: Contract Tests
    runs-on: ubuntu-latest
    timeout-minutes: 15
    needs: [unit, integration]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: "20", cache: "yarn" }
      - run: yarn install --frozen-lockfile
      - run: cp .env.example .env
      - run: yarn test:contract

  security-audit:
    name: Security Audit
    runs-on: ubuntu-latest
    timeout-minutes: 10
    needs: lint-typecheck
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: "20", cache: "yarn" }
      - run: yarn install --frozen-lockfile
      - run: yarn security:audit

  security-tests:
    name: Security Tests
    runs-on: ubuntu-latest
    timeout-minutes: 15
    needs: lint-typecheck
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: "20", cache: "yarn" }
      - run: yarn install --frozen-lockfile
      - run: cp .env.example .env
      - run: yarn test:security

  sast:
    name: SAST (Semgrep)
    runs-on: ubuntu-latest
    timeout-minutes: 20
    needs: lint-typecheck
    container:
      image: semgrep/semgrep
    steps:
      - uses: actions/checkout@v4
      - name: Run Semgrep
        run: semgrep --config=p/typescript --config=p/security-audit --config=p/owasp-top-ten --error --json --output=semgrep-results.json
      - name: Upload SAST report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: sast-report
          path: semgrep-results.json
```
