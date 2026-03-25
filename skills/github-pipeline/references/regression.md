# regression.yml — Nightly Regression Suite

**Customization points**:
- Cron schedule: default is `0 2 * * *` (2 AM UTC). Adjust to the user's timezone preference.
- Currently targets `dev` branch only. To extend to `qa`/`main`, duplicate the jobs with the relevant branch refs, URLs, and API key secrets.
- Slack alert step requires `SLACK_BOT_TOKEN` and `SLACK_ALERTS_CHANNEL` secrets. If user doesn't want Slack alerts, remove the `notify-on-failure` job entirely.

**Adapting for project type**:
- **TypeScript/Node.js**: use as-is (yarn + jest commands)
- **Next.js**: replace `yarn test:e2e` step with `npx playwright install --with-deps && yarn test:e2e`; replace `yarn test:contract` with Playwright contract tests if applicable
- **Python**: replace all Node.js steps with the Python equivalents from `ci-push-python.md`:
  - `actions/setup-node@v4` → `actions/setup-python@v5` with `python-version: "3.12"`
  - `yarn install --frozen-lockfile` → `pip install -r requirements-dev.txt`
  - `yarn test:unit:coverage` → `pytest tests/unit --cov --cov-report=xml`
  - `yarn test:integration` → `pytest tests/integration`
  - `yarn test:contract` → `pytest tests/contract` (or remove if not applicable)
  - `yarn security:audit` → `bandit -r . -c pyproject.toml`
  - `yarn test:security` → `pytest tests/security`
  - `yarn test:smoke` → `pytest tests/smoke`
  - `yarn test:e2e` → `pytest tests/e2e`

```yaml
# Nightly full-suite regression. Catches environment drift and flaky behavior.
# Currently targets dev only. Extend to qa + main when their secrets are configured.
#
# ── GitHub Repository Variables (Settings > Variables > Actions) ──────
# DEV_URL        — https://your-app-dev.yourdomain.com
#
# ── GitHub Repository Secrets (Settings > Secrets > Actions) ──────────
# DEV_API_KEY        — API key for dev environment
# SLACK_BOT_TOKEN    — Slack bot token for failure alerts
# SLACK_ALERTS_CHANNEL — Slack channel ID for failure alerts
name: Nightly Regression

on:
  schedule:
    - cron: "0 2 * * *" # 2:00 AM UTC every night
  workflow_dispatch: # manually triggerable before releases

jobs:
  # ── Unit Tests ───────────────────────────────────────────────────────
  regression-unit:
    name: Unit Tests (Regression)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          ref: dev
      - uses: actions/setup-node@v4
        with: { node-version: "20", cache: "yarn" }
      - run: yarn install --frozen-lockfile
      - run: cp .env.example .env
      - run: yarn test:unit:coverage

  # ── Integration Tests ────────────────────────────────────────────────
  regression-integration:
    name: Integration Tests (Regression)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          ref: dev
      - uses: actions/setup-node@v4
        with: { node-version: "20", cache: "yarn" }
      - run: yarn install --frozen-lockfile
      - run: cp .env.example .env
      - run: yarn test:integration
        env:
          TESTCONTAINERS_RYUK_DISABLED: "true"

  # ── Contract Tests ───────────────────────────────────────────────────
  regression-contract:
    name: Contract Tests (Regression)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          ref: dev
      - uses: actions/setup-node@v4
        with: { node-version: "20", cache: "yarn" }
      - run: yarn install --frozen-lockfile
      - run: cp .env.example .env
      - run: yarn test:contract

  # ── Security Scan ────────────────────────────────────────────────────
  regression-security:
    name: Security Scan (Regression)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          ref: dev
      - uses: actions/setup-node@v4
        with: { node-version: "20", cache: "yarn" }
      - run: yarn install --frozen-lockfile
      - run: cp .env.example .env
      - run: yarn security:audit
      - run: yarn test:security

  # ── SAST ─────────────────────────────────────────────────────────────
  regression-sast:
    name: SAST (Regression)
    runs-on: ubuntu-latest
    container:
      image: semgrep/semgrep
    steps:
      - uses: actions/checkout@v4
        with:
          ref: dev
      - name: Run Semgrep
        run: semgrep --config=p/typescript --config=p/security-audit --config=p/owasp-top-ten --error --json --output=semgrep-results.json
      - name: Upload SAST report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: sast-report
          path: semgrep-results.json

  # ── Smoke Tests (against deployed dev) ───────────────────────────────
  regression-smoke:
    name: Smoke Tests (Regression)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          ref: dev
      - uses: actions/setup-node@v4
        with: { node-version: "20", cache: "yarn" }
      - run: yarn install --frozen-lockfile

      - name: Run smoke tests
        run: yarn test:smoke
        timeout-minutes: 2
        env:
          SMOKE_BASE_URL: ${{ vars.DEV_URL }}
          SMOKE_AUTH_TOKEN: ${{ secrets.DEV_API_KEY }}

  # ── E2E Journey Tests (against deployed dev) ─────────────────────────
  regression-e2e:
    name: E2E Journey Tests (Regression)
    runs-on: ubuntu-latest
    needs: regression-smoke
    steps:
      - uses: actions/checkout@v4
        with:
          ref: dev
      - uses: actions/setup-node@v4
        with: { node-version: "20", cache: "yarn" }
      - run: yarn install --frozen-lockfile

      - name: Run E2E journey tests
        run: yarn test:e2e
        timeout-minutes: 10
        env:
          E2E_BASE_URL: ${{ vars.DEV_URL }}
          E2E_API_KEY: ${{ secrets.DEV_API_KEY }}

  # ── DAST (against deployed dev) ──────────────────────────────────────
  regression-dast:
    name: DAST (Regression)
    runs-on: ubuntu-latest
    needs: regression-e2e
    steps:
      - name: ZAP Baseline Scan
        uses: zaproxy/action-baseline@v0.12.0
        with:
          target: ${{ vars.DEV_URL }}
          fail_action: false
          artifact_name: dast-report

  # ── Slack Alert on Failure ───────────────────────────────────────────
  notify-on-failure:
    name: Slack Alert on Failure
    runs-on: ubuntu-latest
    needs:
      [
        regression-unit,
        regression-integration,
        regression-contract,
        regression-security,
        regression-sast,
        regression-smoke,
        regression-e2e,
        regression-dast,
      ]
    if: failure()
    steps:
      - uses: slackapi/slack-github-action@v1
        with:
          channel-id: ${{ secrets.SLACK_ALERTS_CHANNEL }}
          slack-message: |
            :x: *Nightly Regression Failed* — ${{ github.repository }}
            Branch: `dev`
            Run: ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}
        env:
          SLACK_BOT_TOKEN: ${{ secrets.SLACK_BOT_TOKEN }}
```
