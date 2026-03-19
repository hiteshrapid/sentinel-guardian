---
description: Scan a repository, detect stack, and produce a test plan. First step for any new repo.
---

# /scan

Usage: `/scan <repo-path-or-url> [branch:name]`

## What it does
1. Clones repo (if URL) or uses local path
2. Reads project files to detect framework, DB, auth, package manager
3. Loads matching context from `skills/contexts/`
4. Analyzes existing tests and coverage
5. Produces a test plan with recommended phases
6. Asks for confirmation before spawning agents

## Example
```
/scan /path/to/your/repo branch:main

🔍 Scanning /path/to/your/repo...

Stack Detected:
  Framework:  FastAPI
  Database:   MongoDB (Beanie)
  Auth:       API Key
  Tests:      pytest
  Package:    uv

Existing Tests:
  ✅ Unit: 45 tests (62% coverage)
  ❌ Integration: none
  ❌ Security: none
  ❌ Smoke: none
  ❌ E2E: none

Recommended Plan:
  Phase 1: Unit coverage → 100% (spawn Coverage Agent)
  Phase 2: Integration tests (spawn Integration Agent)
  Phase 3: Security tests (spawn Security Agent)
  Phase 4: Smoke tests (spawn Smoke Agent)
  Phase 5: Verify all green (spawn Verifier)

Proceed? [y/n]
```
