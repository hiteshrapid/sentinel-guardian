# ci-push.yml — Python Merge Checks

Same as the PR Python CI variant but without commit-lint and with `cancel-in-progress: false`.

Also used as the basis for Python `regression.yml` test commands — replace `pytest tests/unit` etc. with the same patterns there.

```yaml
name: CI (Merge)

# Workflow 1b — Runs only on push (merge) to dev/qa/main.
# Triggers "Build and Deploy" workflow via workflow_run.
#
# ── Jobs ──────────────────────────────────────────────────────────────────────
# lint-typecheck → unit          ┐
#               → integration  ┤
#               → security-tests
#               → security-audit
#               → sast

on:
  push:
    branches: [dev, qa, main]
  workflow_dispatch:

concurrency:
  group: ci-push-${{ github.ref }}
  cancel-in-progress: false

jobs:
  lint-typecheck:
    name: Lint + Type Check
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -r requirements-dev.txt
      - name: Lint (ruff)
        run: ruff check .
      - name: Type check (mypy)
        run: mypy .

  unit:
    name: Unit Tests
    runs-on: ubuntu-latest
    timeout-minutes: 15
    needs: lint-typecheck
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -r requirements-dev.txt
      - run: cp .env.example .env
      - run: pytest tests/unit --cov --cov-report=xml
      - name: Upload coverage report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: coverage-report
          path: coverage.xml

  integration:
    name: Integration Tests
    runs-on: ubuntu-latest
    timeout-minutes: 20
    needs: lint-typecheck
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -r requirements-dev.txt
      - run: cp .env.example .env
      - run: pytest tests/integration

  security-audit:
    name: Security Audit (Bandit)
    runs-on: ubuntu-latest
    timeout-minutes: 10
    needs: lint-typecheck
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install bandit
      - run: bandit -r . -c pyproject.toml

  security-tests:
    name: Security Tests
    runs-on: ubuntu-latest
    timeout-minutes: 15
    needs: lint-typecheck
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -r requirements-dev.txt
      - run: cp .env.example .env
      - run: pytest tests/security

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
        run: semgrep --config=p/python --config=p/security-audit --config=p/owasp-top-ten --error --json --output=semgrep-results.json
      - name: Upload SAST report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: sast-report
          path: semgrep-results.json
```
