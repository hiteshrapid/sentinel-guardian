# regression.yml — Python Nightly Regression

Adapt from the Node.js regression template. Replace all Node steps with Python equivalents.

```yaml
name: Nightly Regression

on:
  schedule:
    - cron: "30 20 * * *"  # 2:00 AM IST
  workflow_dispatch:

jobs:
  regression-unit:
    name: Unit Tests (Regression)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: { ref: dev }
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install poetry && poetry install --no-interaction
      - run: cp .env.example .env
      - run: poetry run pytest tests/unit/ -v --cov --cov-report=xml

  regression-integration:
    name: Integration Tests (Regression)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: { ref: dev }
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install poetry && poetry install --no-interaction
      - run: cp .env.example .env
      - run: poetry run pytest tests/integration/ -v

  regression-security:
    name: Security Scan (Regression)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: { ref: dev }
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install bandit
      - run: bandit -r . -c pyproject.toml
      - run: pip install poetry && poetry install --no-interaction
      - run: cp .env.example .env
      - run: poetry run pytest tests/security/ -v

  regression-sast:
    name: SAST (Regression)
    runs-on: ubuntu-latest
    container:
      image: semgrep/semgrep
    steps:
      - uses: actions/checkout@v4
        with: { ref: dev }
      - run: semgrep --config=p/python --config=p/security-audit --config=p/owasp-top-ten --error --json --output=semgrep-results.json
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: sast-report
          path: semgrep-results.json

  regression-smoke:
    name: Smoke Tests (Regression)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: { ref: dev }
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install poetry && poetry install --no-interaction
      - run: cp .env.example .env
      - run: poetry run pytest tests/smoke/ -v --timeout=30
        timeout-minutes: 2
        env:
          SMOKE_BASE_URL: ${{ vars.DEV_URL }}
          SMOKE_AUTH_TOKEN: ${{ secrets.DEV_API_KEY }}

  regression-e2e:
    name: E2E Journey Tests (Regression)
    runs-on: ubuntu-latest
    needs: regression-smoke
    steps:
      - uses: actions/checkout@v4
        with: { ref: dev }
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install poetry && poetry install --no-interaction
      - run: cp .env.example .env
      - run: poetry run pytest tests/e2e/ -v --timeout=300
        timeout-minutes: 10
        env:
          E2E_BASE_URL: ${{ vars.DEV_URL }}
          E2E_API_KEY: ${{ secrets.DEV_API_KEY }}

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

  notify-on-failure:
    name: Slack Alert on Failure
    runs-on: ubuntu-latest
    needs: [regression-unit, regression-integration, regression-security, regression-sast, regression-smoke, regression-e2e, regression-dast]
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
