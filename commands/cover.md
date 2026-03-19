---
description: Push unit test coverage to target percentage. Spawns Coverage Agent.
---

# /cover

Usage: `/cover [target:100]`

## What it does
1. Runs coverage report to find uncovered lines
2. Spawns Coverage Agent with specific uncovered lines
3. Agent writes tests in correct files (never catch-all)
4. Verifies coverage after each batch
5. Reports final coverage

## Example
```
/cover target:100

📊 Current coverage: 92% (148 lines uncovered)
🚀 Spawning Coverage Agent...

... (agent works) ...

✅ Coverage: 100% (0 lines uncovered)
   Added 83 tests across 14 files
   All 2,791 tests passing
```
