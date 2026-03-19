---
description: Generate a comprehensive test suite status report.
---

# /report

Usage: `/report`

## What it does
1. Runs all test suites
2. Collects coverage data
3. Checks CI status
4. Produces a formatted report

## Output
```
🛡️ Sentinel Test Report — {repo-name}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Unit:        2,791 tests | 100% coverage
✅ Integration:    62 tests | all passing
✅ Security:       63 tests | all passing
✅ Contract:       passing  | baseline locked
✅ Smoke:          11 tests | <5s
⬜ E2E:            not configured
✅ CI:             4/4 jobs green

Coverage trend: 92% → 99% → 100% (3 days)
Last CI run: #23180502762 (all green)
```
