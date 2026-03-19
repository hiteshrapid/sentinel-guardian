---
description: Deploy Sentinel — the full testing pyramid. All agents activate, all layers built, 100% coverage, CI wired, PR opened.
---

# /sentinel-deploy

Usage: `/sentinel-deploy <repo-path-or-url> [branch:name]`

> "Sentinel deployed. Target acquired. All units — activate."

## What It Does

Deploys the complete Sentinel testing pyramid on a repo. Every agent activates, every layer gets built, nothing is left uncovered.

```
Phase 0:  Analyzer      → detect stack, produce plan
Phase 1:  Lint Setup     → ruff/ESLint + mypy/tsc --noEmit
Phase 2:  Test Infra     → conftest, fixtures, CI workflows
Phase 3:  Coverage Agent → unit tests → 100% coverage (no exceptions)
Phase 4:  Integration    → all endpoints, real DB, CRUD + errors + auth
Phase 5:  Contract       → OpenAPI/gRPC baseline lock
Phase 6:  Security       → auth, injection, rate limiting, webhook, headers, error responses
Phase 7:  Resilience     → timeout, 5xx, DB failure, Redis failure, circuit breaker
Phase 8:  Smoke          → health, readiness, auth, schema, response time
Phase 9:  Regression     → nightly CI workflow + Slack alerts
Phase 10: Verifier       → all green, 100% coverage, zero test debt
Phase 11: PR             → open against merge target with full report
```

## Execution

1. Clone/cd to repo
2. Identify merge target: `gh pr list --state merged --limit 5`
3. Branch: `test/sentinel-deploy` from merge target
4. Analyzer scans → produces plan
5. **Confirm with the user before proceeding**
6. Phases execute — parallel where safe:
   - Phase 3 + 4 + 6 parallel (unit, integration, security)
   - Phase 5 waits for 3 + 4 (contract needs passing tests)
   - Phase 8 post-deploy only
7. Each phase: write tests → run → fix failures → commit
8. Verifier: full suite → 100% coverage → zero debt
9. Open PR

## CI Pipeline (matches your reference repo)

```
PR:     lint → unit + integration + security (parallel) → contract
Audit:  security-audit (parallel, independent)
Deploy: deploy → smoke → e2e
Night:  ALL layers + Slack alert
```

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

Layer           Tests   Coverage   Status
─────────────────────────────────────────
Lint + Types    —       —          ✅
Unit            X,XXX   100%       ✅
Integration       XX   —          ✅
Contract          XX   —          ✅
Security          XX   —          ✅
Resilience        XX   —          ✅
Smoke             XX   —          ✅
CI Workflow       ✅    X jobs     ✅
Regression        ✅    nightly    ✅

PR: https://github.com/owner/repo/pull/XXX

All units reported. Mission complete. 🛡️
```
