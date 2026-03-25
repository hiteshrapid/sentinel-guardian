# post-deploy.yml — Python Post-Deploy Tests

Runs after "Build and Deploy Application" completes on dev.
Smoke + E2E against the deployed environment.

Adapt the deploy workflow name to match the repo's actual deploy workflow.

```yaml
name: Post-Deploy Tests

on:
  workflow_run:
    workflows: ["Build and Deploy Application"]
    types: [completed]
    branches: [dev]

jobs:
  smoke:
    name: Smoke Tests (dev)
    runs-on: ubuntu-latest
    if: github.event.workflow_run.conclusion == 'success'
    steps:
      - uses: actions/checkout@v4
        with: { ref: dev }
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install poetry && poetry install --no-interaction
      - run: cp .env.example .env
      - name: Wait for service ready
        run: |
          for i in $(seq 1 24); do
            STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${{ vars.DEV_URL }}/health" || echo "000")
            echo "Attempt $i: $STATUS"
            [ "$STATUS" = "200" ] && echo "Ready" && exit 0
            sleep 5
          done
          echo "Service not ready after 2 minutes" && exit 1
      - name: Run smoke tests
        run: poetry run pytest tests/smoke/ -v --timeout=30
        timeout-minutes: 2
        env:
          SMOKE_BASE_URL: ${{ vars.DEV_URL }}
          SMOKE_AUTH_TOKEN: ${{ secrets.DEV_API_KEY }}

  e2e:
    name: E2E Journey Tests (dev)
    runs-on: ubuntu-latest
    needs: smoke
    steps:
      - uses: actions/checkout@v4
        with: { ref: dev }
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install poetry && poetry install --no-interaction
      - run: cp .env.example .env
      - name: Run E2E journey tests
        run: poetry run pytest tests/e2e/ -v --timeout=300
        timeout-minutes: 10
        env:
          E2E_BASE_URL: ${{ vars.DEV_URL }}
          E2E_API_KEY: ${{ secrets.DEV_API_KEY }}

  dast:
    name: DAST - OWASP ZAP (dev)
    runs-on: ubuntu-latest
    needs: e2e
    steps:
      - name: ZAP Baseline Scan
        uses: zaproxy/action-baseline@v0.12.0
        with:
          target: ${{ vars.DEV_URL }}
          fail_action: false
          artifact_name: dast-report
```
