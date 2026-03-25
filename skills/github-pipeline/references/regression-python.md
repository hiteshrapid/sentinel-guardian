# regression.yml — Python Backend Nightly Regression Suite

Adapted from `regression.md` for Python repos using `uv` as the package manager.

Key differences from Node.js:
- `actions/setup-python@v5` + `uv sync --dev` instead of `actions/setup-node@v4` + `yarn install`
- `uv run pytest` for all test commands
- `bandit` for security analysis (replaces `yarn security:audit`)
- `semgrep --config=p/python` instead of `p/typescript`
- Resilience tests included (standard for Python backends with external deps)
- Lint gate (ruff) runs first; contract depends on unit+integration

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
name: Nightly Regression Suite

on:
  schedule:
    - cron: "0 2 * * *" # 2:00 AM UTC every night
  workflow_dispatch: # manually triggerable before releases

jobs:
  # ── Unit Tests ───────────────────────────────────────────────────────
  regression-lint:
    name: Lint + Type Check (Regression)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: { ref: dev }
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - name: Install uv
        uses: astral-sh/setup-uv@v4
      - run: uv sync --dev
      - run: cp .env.example .env
      - run: uv run ruff check .
      - run: uv run ruff format --check .

  regression-unit:
    name: Unit Tests (Regression)
    runs-on: ubuntu-latest
    needs: regression-lint
    steps:
      - uses: actions/checkout@v4
        with: { ref: dev }
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - name: Install uv
        uses: astral-sh/setup-uv@v4
      - run: uv sync --dev
      - run: cp .env.example .env
      - run: uv run pytest tests/unit/ -v --cov --cov-report=term-missing --cov-fail-under=100

  # ── Integration Tests ────────────────────────────────────────────────
  regression-integration:
    name: Integration Tests (Regression)
    runs-on: ubuntu-latest
    needs: regression-lint
    steps:
      - uses: actions/checkout@v4
        with: { ref: dev }
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - name: Install uv
        uses: astral-sh/setup-uv@v4
      - run: uv sync --dev
      - run: cp .env.example .env
      - run: uv run pytest tests/integration/ -v

  # ── Security Tests ──────────────────────────────────────────────────
  regression-security-tests:
    name: Security Tests (Regression)
    runs-on: ubuntu-latest
    needs: regression-lint
    steps:
      - uses: actions/checkout@v4
        with: { ref: dev }
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - name: Install uv
        uses: astral-sh/setup-uv@v4
      - run: uv sync --dev
      - run: cp .env.example .env
      - run: uv run pytest tests/security/ -v

  # ── Resilience Tests ─────────────────────────────────────────────────
  regression-resilience:
    name: Resilience Tests (Regression)
    runs-on: ubuntu-latest
    needs: regression-lint
    steps:
      - uses: actions/checkout@v4
        with: { ref: dev }
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - name: Install uv
        uses: astral-sh/setup-uv@v4
      - run: uv sync --dev
      - run: cp .env.example .env
      - run: uv run pytest tests/resilience/ -v

  # ── Contract Tests ───────────────────────────────────────────────────
  regression-contract:
    name: Contract Tests (Regression)
    runs-on: ubuntu-latest
    needs: [regression-unit, regression-integration]
    steps:
      - uses: actions/checkout@v4
        with: { ref: dev }
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - name: Install uv
        uses: astral-sh/setup-uv@v4
      - run: uv sync --dev
      - run: cp .env.example .env
      - run: uv run pytest tests/contract/ -v

  # ── Security Scan ────────────────────────────────────────────────────
  regression-audit:
    name: Security Audit (Regression)
    runs-on: ubuntu-latest
    continue-on-error: true
    steps:
      - uses: actions/checkout@v4
        with: { ref: dev }
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - name: Install uv
        uses: astral-sh/setup-uv@v4
      - run: uv sync --dev
      - name: Audit third-party dependencies
        run: |
          uv export --no-hashes --frozen > requirements.txt
          PACKAGE_NAME=$(grep '^name' pyproject.toml | head -1 | sed 's/.*= *"\(.*\)"/\1/')
          grep -v "$PACKAGE_NAME" requirements.txt > requirements-audit.txt || true
          pip install pip-audit
          pip-audit -r requirements-audit.txt

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
        run: semgrep --config=p/python --config=p/security-audit --config=p/owasp-top-ten --error --json --output=semgrep-results.json
      - name: Upload SAST report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: sast-report
          path: semgrep-results.json

  # ── Smoke Tests (against deployed dev) ───────────────────────────────
  regression-smoke:
    name: Smoke Tests vs Staging (Regression)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: { ref: dev }
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - name: Install uv
        uses: astral-sh/setup-uv@v4
      - run: uv sync --dev
      - run: cp .env.example .env
      - name: Run smoke tests
        run: uv run pytest tests/smoke/ -v --timeout=60
        timeout-minutes: 2
        env:
          SMOKE_BASE_URL: ${{ vars.DEV_URL }}
          SMOKE_AUTH_TOKEN: ${{ secrets.DEV_API_KEY }}

  # ── E2E Journey Tests (against deployed dev) ─────────────────────────
  regression-e2e:
    name: E2E Journey Tests (live)
    runs-on: ubuntu-latest
    needs: regression-smoke
    steps:
      - uses: actions/checkout@v4
        with: { ref: dev }
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - name: Install uv
        uses: astral-sh/setup-uv@v4
      - run: uv sync --dev
      - run: cp .env.example .env
      - name: Run E2E tests
        run: uv run pytest tests/e2e/ -v --timeout=300
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
        regression-lint,
        regression-unit,
        regression-integration,
        regression-security-tests,
        regression-audit,
        regression-resilience,
        regression-contract,
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
