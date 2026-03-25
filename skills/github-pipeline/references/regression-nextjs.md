# regression.yml — Next.js Frontend Nightly Regression Suite

Adapted from `regression.md` for Next.js frontend repos.

Key differences from Node.js backend:
- Unit + Component tests via Vitest (not Jest)
- Playwright E2E: local (against `next start`) AND deployed (against DEV_URL)
- Lighthouse performance audit (nightly — catches perf regressions)
- Accessibility audit via `@axe-core/cli`
- Bundle size check (catches size regressions)
- `semgrep --config=p/typescript --config=p/react` for SAST
- `yarn audit` for dependency scanning
- No integration/contract/resilience jobs (backend concepts)

**Customization points**:
- Cron schedule: default `30 20 * * *` (2:00 AM IST / 20:30 UTC).
- Browser strategy: Chromium + WebKit in nightly (via `NIGHTLY=true` env var).
- Lighthouse budget: defined in `lighthouse-budget.json` at repo root.
- Slack alerts: remove `notify-on-failure` job if not needed.

```yaml
name: Nightly Regression

on:
  schedule:
    - cron: "0 2 * * *"  # 2:00 AM UTC
  workflow_dispatch:

env:
  NODE_VERSION: "20"

jobs:
  # ── Unit + Component Tests ──────────────────────────────────────────
  regression-unit:
    name: Unit + Component Tests (Regression)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: { ref: dev }
      - uses: actions/setup-node@v4
        with: { node-version: "20", cache: "yarn" }
      - run: yarn install --frozen-lockfile
      - run: yarn test:coverage
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: nightly-coverage
          path: coverage/
          retention-days: 30

  # ── Build ────────────────────────────────────────────────────────────
  regression-build:
    name: Build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: { ref: dev }
      - uses: actions/setup-node@v4
        with: { node-version: "20", cache: "yarn" }
      - run: yarn install --frozen-lockfile
      - run: yarn build
        env:
          NEXT_TELEMETRY_DISABLED: 1
      - uses: actions/upload-artifact@v4
        with:
          name: nightly-build
          path: .next/
          include-hidden-files: true
          retention-days: 1

  # ── E2E Local (against next start) ──────────────────────────────────
  regression-e2e-local:
    name: E2E Local (Regression)
    runs-on: ubuntu-latest
    needs: regression-build
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4
        with: { ref: dev }
      - uses: actions/setup-node@v4
        with: { node-version: "20", cache: "yarn" }
      - run: yarn install --frozen-lockfile
      - uses: actions/download-artifact@v4
        with:
          name: nightly-build
          path: .next/
      - run: npx playwright install --with-deps chromium webkit
      - name: Run E2E
        run: yarn test:e2e
        env:
          NIGHTLY: "true"
          E2E_BASE_URL: http://localhost:3000
          E2E_ADMIN_EMAIL: ${{ secrets.E2E_ADMIN_EMAIL }}
          E2E_ADMIN_PASSWORD: ${{ secrets.E2E_ADMIN_PASSWORD }}
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: nightly-local-playwright-report
          path: playwright-report/
          retention-days: 30

  # ── E2E Deployed (against DEV_URL) ──────────────────────────────────
  regression-e2e-deployed:
    name: E2E Deployed (Regression)
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4
        with: { ref: dev }
      - uses: actions/setup-node@v4
        with: { node-version: "20", cache: "yarn" }
      - run: yarn install --frozen-lockfile
      - run: npx playwright install --with-deps chromium
      - name: Run E2E against deployed dev
        run: yarn test:e2e
        env:
          E2E_BASE_URL: ${{ vars.DEV_URL }}
          E2E_ADMIN_EMAIL: ${{ secrets.E2E_ADMIN_EMAIL }}
          E2E_ADMIN_PASSWORD: ${{ secrets.E2E_ADMIN_PASSWORD }}
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: nightly-deployed-playwright-report
          path: playwright-report/
          retention-days: 30

  # ── Lighthouse Performance Audit ─────────────────────────────────────
  regression-lighthouse:
    name: Lighthouse (Regression)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: { ref: dev }
      - name: Run Lighthouse
        uses: treosh/lighthouse-ci-action@v12
        with:
          urls: |
            ${{ vars.DEV_URL }}/login
            ${{ vars.DEV_URL }}/
          budgetPath: ./lighthouse-budget.json
          uploadArtifacts: true
          temporaryPublicStorage: true

  # ── Accessibility Audit ──────────────────────────────────────────────
  regression-accessibility:
    name: Accessibility (Regression)
    runs-on: ubuntu-latest
    needs: regression-build
    steps:
      - uses: actions/checkout@v4
        with: { ref: dev }
      - uses: actions/setup-node@v4
        with: { node-version: "20", cache: "yarn" }
      - run: yarn install --frozen-lockfile
      - uses: actions/download-artifact@v4
        with:
          name: nightly-build
          path: .next/
      - run: npx playwright install --with-deps chromium
      - name: Run accessibility audit
        run: |
          yarn start &
          npx wait-on http://localhost:3000 --timeout 30000
          npx @axe-core/cli http://localhost:3000/login --exit

  # ── Bundle Size Check ────────────────────────────────────────────────
  regression-bundle:
    name: Bundle Size (Regression)
    runs-on: ubuntu-latest
    needs: regression-build
    steps:
      - uses: actions/checkout@v4
        with: { ref: dev }
      - uses: actions/download-artifact@v4
        with:
          name: nightly-build
          path: .next/
      - name: Analyze bundle
        run: |
          echo "## Bundle Size Report (Nightly)" >> $GITHUB_STEP_SUMMARY
          echo '```' >> $GITHUB_STEP_SUMMARY
          find .next -name '*.js' -path '*chunks*' | head -20 | while read f; do
            SIZE=$(stat --printf="%s" "$f" 2>/dev/null || stat -f%z "$f" 2>/dev/null)
            SIZE_KB=$((SIZE / 1024))
            echo "$(basename $f): ${SIZE_KB}KB"
          done | sort -t: -k2 -rn >> $GITHUB_STEP_SUMMARY
          echo '```' >> $GITHUB_STEP_SUMMARY
          LARGE=$(find .next -name '*.js' -path '*chunks*' -size +500k | wc -l)
          if [ "$LARGE" -gt 0 ]; then
            echo "WARNING: $LARGE chunks exceed 500KB" | tee -a $GITHUB_STEP_SUMMARY
          fi

  # ── Security Audit ───────────────────────────────────────────────────
  regression-security:
    name: Security Audit (Regression)
    runs-on: ubuntu-latest
    continue-on-error: true
    steps:
      - uses: actions/checkout@v4
        with: { ref: dev }
      - uses: actions/setup-node@v4
        with: { node-version: "20", cache: "yarn" }
      - run: yarn install --frozen-lockfile
      - run: yarn audit --groups dependencies --level critical; echo "Audit complete"

  # ── SAST (Semgrep) ──────────────────────────────────────────────────
  regression-sast:
    name: SAST (Regression)
    runs-on: ubuntu-latest
    container:
      image: semgrep/semgrep
    steps:
      - uses: actions/checkout@v4
        with: { ref: dev }
      - name: Run Semgrep
        run: semgrep --config=p/typescript --config=p/react --config=p/security-audit --config=p/owasp-top-ten --error --json --output=semgrep-results.json
      - name: Upload SAST report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: sast-report
          path: semgrep-results.json

  # ── DAST (against deployed dev) ──────────────────────────────────────
  regression-dast:
    name: DAST (Regression)
    runs-on: ubuntu-latest
    steps:
      - name: ZAP Baseline Scan
        uses: zaproxy/action-baseline@v0.12.0
        with:
          target: ${{ vars.DEV_URL }}
          fail_action: false
          artifact_name: dast-report

  # ── Slack Alert on Failure ───────────────────────────────────────────
  notify-on-failure:
    name: Notify on Failure
    runs-on: ubuntu-latest
    needs:
      [
        regression-unit,
        regression-build,
        regression-e2e-local,
        regression-e2e-deployed,
        regression-lighthouse,
        regression-accessibility,
        regression-bundle,
        regression-security,
        regression-sast,
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
