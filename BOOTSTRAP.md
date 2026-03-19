# BOOTSTRAP.md — Sentinel Repo Onboarding Checklist

Use this whenever Sentinel is attached to a new repo for the first time.

## 1. Identify the Repo
- GitHub slug (owner/name)
- Local clone path
- Default branch / actual merge target
- Tier (P1 / P2 / experimental)

## 2. Detect the Stack
- framework
- database / persistence layer
- auth model
- package manager / runtime
- test runner
- existing CI workflow files

## 3. Load the Right Context
Match an existing file in `contexts/`. If missing, create a new one before scaling work.

## 4. Baseline Current Quality
- existing test suites and their status
- current CI health
- current coverage %
- existing smoke/e2e/regression workflows
- known flaky tests / skips / xfails

## 5. Add Repo Record
Update AGENTS.md and HEARTBEAT.md:

```yaml
repo: owner/name
local_path: /absolute/path
primary_branch: dev
stack: fastapi-beanie
ci_workflow: CI Tests
regression_workflow: Nightly Regression Suite
smoke_enabled: true
e2e_enabled: false
priority: P1
status: active
```

## 6. Decide Phase Order

Standard order:
1. setup (conftest, fixtures, CI wiring)
2. unit
3. integration
4. contract
5. security
6. smoke
7. e2e (if UI exists)
8. regression wiring

## 7. Agent Rules Before Writing Tests
- NEVER create catch-all test files
- verify method names before mocking
- read current source after merges
- run tests after every edit
- use fresh branches from the real merge target

## 8. Close the Loop
- update `LEARNINGS.md`
- add dated memory file in `memory/`
- update affected context / agent files
- confirm heartbeat knows how to monitor this repo
