# ci-push.yml — Next.js Frontend Merge Checks

Same as the PR Next.js CI variant but without commit-lint and with cancel-in-progress: false.

Complete frontend merge CI pipeline for Next.js repos. Includes unit+component tests, build verification,
local E2E via Playwright, Lighthouse performance audit, bundle size check, security audit, and SAST.

No integration/contract/resilience jobs — those are backend concepts.

```yaml
name: CI (Merge)

# lint-typecheck -> unit-component
#                                -> build -> e2e-local
#                                         -> lighthouse
#                                         -> bundle-size
#                                -> security-audit
#                                -> sast

on:
  push:
    branches: [dev, qa, main]
  workflow_dispatch:

concurrency:
  group: ci-push-${{ github.ref }}
  cancel-in-progress: false

env:
  FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: "true"
  NEXT_TELEMETRY_DISABLED: 1

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
      - run: yarn lint
      - run: npx tsc --noEmit

  unit-component:
    name: Unit + Component Tests
    runs-on: ubuntu-latest
    timeout-minutes: 15
    needs: lint-typecheck
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: "20", cache: "yarn" }
      - run: yarn install --frozen-lockfile
      - run: yarn test:coverage
      - name: Upload coverage report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: coverage-report
          path: coverage/

  build:
    name: Build
    runs-on: ubuntu-latest
    timeout-minutes: 15
    needs: lint-typecheck
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: "20", cache: "yarn" }
      - run: yarn install --frozen-lockfile
      - name: Cache Next.js build
        uses: actions/cache@v4
        with:
          path: .next/cache
          key: nextjs-${{ runner.os }}-${{ hashFiles('yarn.lock') }}-${{ hashFiles('src/**/*.ts', 'src/**/*.tsx') }}
          restore-keys: |
            nextjs-${{ runner.os }}-${{ hashFiles('yarn.lock') }}-
            nextjs-${{ runner.os }}-
      - run: yarn build
      - uses: actions/upload-artifact@v4
        with:
          name: build-output
          path: .next/
          include-hidden-files: true
          retention-days: 1

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
      - run: yarn lint
      - run: npx tsc --noEmit

  unit-component:
    name: Unit + Component Tests
    runs-on: ubuntu-latest
    timeout-minutes: 15
    needs: lint-typecheck
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: "20", cache: "yarn" }
      - run: yarn install --frozen-lockfile
      - run: yarn test:coverage
      - name: Upload coverage report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: coverage-report
          path: coverage/
          retention-days: 14

  build:
    name: Build
    runs-on: ubuntu-latest
    timeout-minutes: 15
    needs: lint-typecheck
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: "20", cache: "yarn" }
      - run: yarn install --frozen-lockfile
      - name: Cache Next.js build
        uses: actions/cache@v4
        with:
          path: .next/cache
          key: nextjs-${{ runner.os }}-${{ hashFiles('yarn.lock') }}-${{ hashFiles('src/**/*.ts', 'src/**/*.tsx') }}
          restore-keys: |
            nextjs-${{ runner.os }}-${{ hashFiles('yarn.lock') }}-
            nextjs-${{ runner.os }}-
      - run: yarn build
      - uses: actions/upload-artifact@v4
        with:
          name: build-output
          path: .next/
          include-hidden-files: true
          retention-days: 1

  e2e-local:
    name: E2E Tests (Local)
    runs-on: ubuntu-latest
    timeout-minutes: 15
    needs: build
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: "20", cache: "yarn" }
      - run: yarn install --frozen-lockfile
      - uses: actions/download-artifact@v4
        with:
          name: build-output
          path: .next/
      - run: npx playwright install --with-deps chromium
      - name: Run E2E tests
        run: yarn test:e2e
      - uses: actions/upload-artifact@v4
        if: failure()
        with:
          name: playwright-report
          path: playwright-report/
          retention-days: 7

  lighthouse:
    name: Lighthouse Performance Audit
    runs-on: ubuntu-latest
    timeout-minutes: 10
    needs: build
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: "20", cache: "yarn" }
      - run: yarn install --frozen-lockfile
      - uses: actions/download-artifact@v4
        with:
          name: build-output
          path: .next/
      - name: Start server
        run: yarn start &
      - name: Wait for server
        run: npx wait-on http://localhost:3000 --timeout 30000
      - name: Run Lighthouse
        run: npx @lhci/cli autorun --collect.url=http://localhost:3000/login --collect.url=http://localhost:3000/ --assert.assertions.first-contentful-paint=["error",{"maxNumericValue":2000}] --assert.assertions.largest-contentful-paint=["error",{"maxNumericValue":3000}]

  bundle-size:
    name: Bundle Size Check
    runs-on: ubuntu-latest
    timeout-minutes: 5
    needs: build
    steps:
      - uses: actions/checkout@v4
      - uses: actions/download-artifact@v4
        with:
          name: build-output
          path: .next/
      - name: Analyze bundle
        run: |
          LARGE=$(find .next -name '*.js' -path '*chunks*' -size +500k | wc -l)
          if [ "$LARGE" -gt 0 ]; then
            echo "FAIL: $LARGE chunks exceed 500KB" && exit 1
          fi
          echo "All chunks under 500KB"

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
      - run: yarn audit --groups dependencies --level high

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
        run: semgrep --config=p/typescript --config=p/react --config=p/security-audit --config=p/owasp-top-ten --error --json --output=semgrep-results.json
      - name: Upload SAST report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: sast-report
          path: semgrep-results.json
```
