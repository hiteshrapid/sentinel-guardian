# ci.yml — PR Checks

```yaml
name: CI

# Workflow 1a — Runs on every PR to dev/qa/main.
# Does NOT trigger Build and Deploy (only ci-push.yml does).
#
# ── Jobs ──────────────────────────────────────────────────────────────────────
# commit-lint → lint-typecheck → unit          ┐
#                              → integration  ┤→ contract
#                              → security-tests
#                              → security-audit
#                              → sast

on:
  pull_request:
    branches: [dev, qa, main]
    types: [opened, synchronize, reopened, ready_for_review]
  workflow_dispatch:

# Cancel in-progress CI when new commits are pushed to the same PR.
concurrency:
  group: ci-pr-${{ github.ref }}
  cancel-in-progress: true

env:
  FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: "true"

jobs:
  commit-lint:
    name: Commit Message Lint
    if: github.event.pull_request.draft != true
    uses: ./.github/workflows/commit-lint.yml

  lint-typecheck:
    name: Lint + Type Check
    if: github.event.pull_request.draft != true
    needs: commit-lint
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
