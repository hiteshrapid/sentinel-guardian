---
description: Diagnose and fix CI failures. Reads CI logs and applies targeted fixes.
---

# /fix-ci

Usage: `/fix-ci [run-id]`

## What it does
1. Fetches latest CI run (or specified run-id)
2. Reads failure logs
3. Identifies root cause pattern (routing, imports, mocks, env vars)
4. Applies targeted fix
5. Pushes and monitors new CI run

## Example
```
/fix-ci

🔍 Fetching CI run #23180502762...
❌ Integration Tests: 25 failures

Root cause: httpx not following 307 redirects
Fix: add follow_redirects=True to AsyncClient

✅ Fix applied and pushed
🔄 CI running... all green!
```
