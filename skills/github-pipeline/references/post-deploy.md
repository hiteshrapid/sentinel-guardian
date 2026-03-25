# post-deploy.yml — Smoke, E2E, and DAST Tests

```yaml
name: Post-Deploy Tests
run-name: Post-Deploy Tests (${{ github.event.workflow_run.head_branch }})

# Workflow 3 — Triggered automatically when Build and Deploy succeeds on dev, qa, or main.
# Runs smoke tests → E2E journey tests → DAST scan against the deployed environment.
#
# ── Secrets required (via repo secrets) ───────────────────────────────────────
# DEV_API_KEY, QA_API_KEY, PROD_API_KEY
#
# ── Variables required ────────────────────────────────────────────────────────
# DEV_URL, QA_URL, PROD_URL

on:
  workflow_run:
    workflows: ["Build and Deploy"]
    types: [completed]
    branches: [dev, qa, main]

concurrency:
  group: post-deploy-${{ github.event.workflow_run.head_branch }}
  cancel-in-progress: false

env:
  FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: "true"

jobs:
  # Resolves target environment and validates that the deploy succeeded.
  # All downstream jobs need this one — if deploy failed, everything skips.
  resolve-env:
    name: Resolve Environment
    runs-on: ubuntu-latest
    if: github.event.workflow_run.conclusion == 'success'
    outputs:
      env_name: ${{ steps.resolve.outputs.env_name }}
      base_url: ${{ steps.resolve.outputs.base_url }}
    steps:
      - name: Resolve environment from branch
        id: resolve
        env:
          # build-deploy.yml uses a push trigger so head_branch is always the real pushed branch.
          BRANCH:   ${{ github.event.workflow_run.head_branch }}
          PROD_URL: ${{ vars.PROD_URL }}
          QA_URL:   ${{ vars.QA_URL }}
          DEV_URL:  ${{ vars.DEV_URL }}
        run: |
          echo "Resolved branch: $BRANCH"
          if [ "$BRANCH" = "main" ]; then
            echo "env_name=prod" >> $GITHUB_OUTPUT
            echo "base_url=$PROD_URL" >> $GITHUB_OUTPUT
          elif [ "$BRANCH" = "qa" ]; then
            echo "env_name=qa" >> $GITHUB_OUTPUT
            echo "base_url=$QA_URL" >> $GITHUB_OUTPUT
          else
            echo "env_name=dev" >> $GITHUB_OUTPUT
            echo "base_url=$DEV_URL" >> $GITHUB_OUTPUT
          fi

  smoke:
    name: Smoke Tests (${{ needs.resolve-env.outputs.env_name }})
    needs: resolve-env
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4 # nosemgrep: yaml.github-actions.security.workflow-run-target-code-checkout.workflow-run-target-code-checkout
        with:
          ref: ${{ github.event.workflow_run.head_branch }} # safe: push-only, protected branches (dev/qa/main)
      - uses: actions/setup-node@v4
        with: { node-version: "20", cache: "yarn" }
      - run: yarn install --frozen-lockfile
      - name: Wait for service ready
        env:
          BASE_URL: ${{ needs.resolve-env.outputs.base_url }}
        run: |
          for i in $(seq 1 24); do
            STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/health" || echo "000")
            echo "Attempt $i: $STATUS"
            [ "$STATUS" = "200" ] && echo "Ready" && exit 0
            sleep 5
          done
          echo "Service not ready after 2 minutes" && exit 1
      - name: Run smoke tests
        run: yarn test:smoke
        timeout-minutes: 2
        env:
          SMOKE_BASE_URL: ${{ needs.resolve-env.outputs.base_url }}
          SMOKE_AUTH_TOKEN: >-
            ${{ needs.resolve-env.outputs.env_name == 'prod' && secrets.PROD_API_KEY
             || needs.resolve-env.outputs.env_name == 'qa'   && secrets.QA_API_KEY
             || needs.resolve-env.outputs.env_name == 'dev'  && secrets.DEV_API_KEY }}

  e2e:
    name: E2E Journey Tests (${{ needs.resolve-env.outputs.env_name }})
    needs: [resolve-env, smoke]
    runs-on: ubuntu-latest
    timeout-minutes: 20
    steps:
      - uses: actions/checkout@v4 # nosemgrep: yaml.github-actions.security.workflow-run-target-code-checkout.workflow-run-target-code-checkout
        with:
          ref: ${{ github.event.workflow_run.head_branch }} # safe: push-only, protected branches (dev/qa/main)
      - uses: actions/setup-node@v4
        with: { node-version: "20", cache: "yarn" }
      - run: yarn install --frozen-lockfile
      - name: Run E2E journey tests
        run: yarn test:e2e
        timeout-minutes: 10
        env:
          E2E_BASE_URL: ${{ needs.resolve-env.outputs.base_url }}
          E2E_API_KEY: >-
            ${{ needs.resolve-env.outputs.env_name == 'prod' && secrets.PROD_API_KEY
             || needs.resolve-env.outputs.env_name == 'qa'   && secrets.QA_API_KEY
             || needs.resolve-env.outputs.env_name == 'dev'  && secrets.DEV_API_KEY }}

  dast:
    name: DAST - OWASP ZAP (${{ needs.resolve-env.outputs.env_name }})
    needs: [resolve-env, e2e]
    runs-on: ubuntu-latest
    timeout-minutes: 20
    steps:
      - name: ZAP Baseline Scan
        uses: zaproxy/action-baseline@v0.12.0
        with:
          target: ${{ needs.resolve-env.outputs.base_url }}
          fail_action: false
          artifact_name: dast-report-${{ needs.resolve-env.outputs.env_name }}
```
