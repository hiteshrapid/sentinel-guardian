---
description: Deploy Sentinel — the full testing pyramid. All agents activate, all layers built, 100% coverage, CI wired, PR opened.
---

# /sentinel-deploy

Usage: `/sentinel-deploy <repo-path-or-url> [branch:name]`

> "Sentinel deployed. Target acquired. All units — activate."

## What It Does

Deploys the complete Sentinel testing pyramid on a repo. Every agent activates, every layer gets built, nothing is left uncovered.

```
Phase 0:  Analyzer       → detect stack, produce plan
Phase 1:  Lint Setup      → ruff/ESLint + mypy/tsc --noEmit
Phase 2:  Test Infra      → conftest, fixtures, CI workflows (all 7 canonical)
Phase 3:  Unit Tests      → 100% coverage (no exceptions)
Phase 3b: Component Tests → (frontend only) React components via Vitest + Testing Library, 100% coverage
Phase 4:  Integration     → all endpoints, real DB, CRUD + errors + auth
Phase 5:  Contract        → OpenAPI/gRPC baseline lock
Phase 6:  Security Tests  → auth, injection, rate limiting, webhook, headers, error responses
Phase 7:  Security Audit  → Bandit (Python) / yarn audit (JS) + pip-audit dependency scan
Phase 8:  SAST            → Semgrep static analysis (p/python or p/typescript + p/react)
Phase 9:  Resilience      → timeout, 5xx, DB failure, Redis failure, circuit breaker
Phase 10: Smoke           → health, readiness, auth, schema, response time
Phase 11: Regression      → nightly CI workflow + SAST + DAST (OWASP ZAP) + Slack alerts
Phase 12: Verifier        → all green, 100% coverage, zero test debt
Phase 13: PR              → open against merge target with full report
```

## Execution

1. Clone/cd to repo
2. Identify merge target: `gh pr list --state merged --limit 5`
3. Branch: `test/sentinel-deploy` from merge target
4. Analyzer scans → produces plan
5. **Confirm with the user before proceeding**
6. Phases execute — parallel where safe:
   - Phase 3 + 4 + 6 + 7 + 8 parallel (unit, integration, security-tests, security-audit, SAST)
   - Phase 5 waits for 3 + 4 (contract needs passing tests)
   - Phase 10 post-deploy only
7. Each phase: write tests → run → fix failures → commit
8. Verifier: full suite → 100% coverage → zero debt
9. Open PR

## CI Pipeline (matches gold standard: communication-channel-service)

```
PR CI:
  commit-lint → lint-typecheck → unit            ┐
                               → integration    ┤→ contract
                               → security-tests
                               → security-audit
                               → sast (Semgrep)

Post-deploy:
  smoke → e2e → dast (OWASP ZAP)

Nightly regression:
  ALL of the above + Slack alerts on failure
```

All three security jobs (security-tests, security-audit, sast) are parallel siblings with `needs: lint-typecheck`.

## Non-Negotiables

- 100% unit coverage — every line, every branch
- Every endpoint gets integration tests
- Contract baseline committed to repo
- Security covers all 6 categories
- Lint is the first CI gate
- Fresh branch from actual merge target
- Commit after each passing phase
- Never create catch-all test files
- Verify method names before mocking

## Completion Report

```
🛡️ SENTINEL DEPLOYED — Mission Complete
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Target: {repo-name}
Branch: test/sentinel-deploy → {merge-target}

Layer            Tests   Coverage   Status
──────────────────────────────────────────
Lint + Types     —       —          ✅
Unit             X,XXX   100%       ✅
Component        X,XXX   100%       ✅ (frontend only)
Integration        XX    —          ✅
Contract           XX    —          ✅
Security Tests     XX    —          ✅
Security Audit     —     —          ✅ (Bandit + pip-audit)
SAST (Semgrep)     —     —          ✅
Resilience         XX    —          ✅
Smoke              XX    —          ✅
DAST (ZAP)         —     —          ✅ (post-deploy)
CI Workflows       ✅    7 files    ✅
Regression         ✅    nightly    ✅

PR: https://github.com/owner/repo/pull/XXX

All units reported. Mission complete. 🛡️
```
