# ci.yml — Python PR Checks

Key differences from Node.js:
- Uses `python` + `pip` instead of `node` + `yarn`
- `ruff` for linting, `mypy` for type checking
- `pytest` + `pytest-cov` for unit/integration tests
- `bandit` for security scanning (replaces `yarn audit`)
- `contract` job needs [unit, integration]
- Semgrep uses `p/python` ruleset

**Required Python tooling** (add to `pyproject.toml` or `requirements-dev.txt`):
```
pytest
pytest-cov
ruff
mypy
bandit[toml]
semgrep
```

**Required `pytest` test structure** (adjust `testpaths` in `pytest.ini` / `pyproject.toml` as needed):
```
tests/
  unit/
  integration/
  security/
  smoke/
  e2e/
```

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

concurrency:
  group: ci-pr-${{ github.ref }}
  cancel-in-progress: true

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
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - name: Install uv
        uses: astral-sh/setup-uv@v4
      - run: uv sync --dev
      - name: Lint (ruff)
        run: uv run ruff check .
      - name: Type check (mypy)
        run: uv run mypy . --ignore-missing-imports

  unit:
    name: Unit Tests
    runs-on: ubuntu-latest
    timeout-minutes: 15
    needs: lint-typecheck
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - name: Install uv
        uses: astral-sh/setup-uv@v4
      - run: uv sync --dev
      - run: cp .env.example .env
      - run: uv run pytest tests/unit/ -v --cov --cov-report=term-missing --cov-fail-under=100
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
        with: { python-version: "3.11" }
      - name: Install uv
        uses: astral-sh/setup-uv@v4
      - run: uv sync --dev
      - run: cp .env.example .env
      - run: uv run pytest tests/integration/ -v

  security-audit:
    name: Security Audit
    runs-on: ubuntu-latest
    timeout-minutes: 10
    needs: lint-typecheck
    continue-on-error: true
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - name: Install uv
        uses: astral-sh/setup-uv@v4
      - run: uv sync --dev
      - name: Bandit static analysis
        run: uv run bandit -r . -c pyproject.toml -ll -ii
      - name: pip-audit dependency scan
        run: |
          uv export --no-hashes --frozen > /tmp/reqs.txt
          PACKAGE_NAME=$(grep '^name' pyproject.toml | head -1 | sed 's/.*= *"\(.*\)"/\1/')
          grep -v "$PACKAGE_NAME" /tmp/reqs.txt > /tmp/reqs-audit.txt || true
          pip install pip-audit
          pip-audit -r /tmp/reqs-audit.txt

  security-tests:
    name: Security Tests
    runs-on: ubuntu-latest
    timeout-minutes: 15
    needs: lint-typecheck
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - name: Install uv
        uses: astral-sh/setup-uv@v4
      - run: uv sync --dev
      - run: cp .env.example .env
      - run: uv run pytest tests/security/ -v

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

  contract:
    name: Contract Tests
    runs-on: ubuntu-latest
    timeout-minutes: 15
    needs: [unit, integration]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - name: Install uv
        uses: astral-sh/setup-uv@v4
      - run: uv sync --dev
      - run: cp .env.example .env
      - run: uv run pytest tests/contract/ -v
```
