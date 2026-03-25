---
description: Watch active PRs across connected repos. Monitor for new comments, review requests, and CI failures. Respond to PR feedback automatically.
---

# /sentinel-watch

Usage: `/sentinel-watch [repo]`

> Sentinel on overwatch. Monitoring all active PRs.

## What It Does

Monitors active PRs across connected repos and:
1. **Detects new review comments** → reads, understands, and addresses them
2. **Detects CI failures on PRs** → diagnoses and fixes
3. **Detects requested changes** → implements the requested changes
4. **Reports status** → concise summary of PR health

## Execution

```bash
# Check all connected repos
for repo in connected_repos:
    # 1. List open PRs
    gh pr list --repo $repo --state open --json number,title,reviewDecision,statusCheckRollup

    # 2. For each PR with activity:
    #    - Read new comments: gh pr view $number --comments
    #    - Check CI status: gh pr checks $number
    #    - If comments need code changes → checkout PR branch, fix, push
    #    - If CI failed → spawn CI Fix Agent
    #    - If review requested changes → implement them

    # 3. Report
```

## Comment Response Flow

```
New comment detected on PR #123
    ↓
Read comment content
    ↓
├── Code change requested → checkout branch, make change, push, reply
├── Question asked → reply with answer
├── Approval → note it, no action
├── Nitpick/style → fix it, push, reply "Fixed"
└── Disagreement → flag to the user, don't auto-resolve
```

## Rules

- **Jira ticket required for all fix work** — for CI fixes on existing PRs, use the PR's existing ticket ID. For new fix branches, create a TT ticket first.

- **Never force-push** — always new commits on PR branches
- **Reply to every actionable comment** — don't leave reviewers hanging
- **Flag disagreements to the user** — don't auto-resolve subjective feedback
- **Fix CI before addressing comments** — green CI first
- **One commit per comment thread** — clean history
- **Run tests after every fix** — never push broken code

## Report Format

```
🛡️ Sentinel Watch Report
━━━━━━━━━━━━━━━━━━━━━━━

org/backend-api
  PR #45: "Add email templates" — ✅ approved, CI green
  PR #47: "Fix scheduler bug" — ⚠️ 2 comments pending
    → @reviewer: "Can you add a test for the edge case?" — fixing...

org/frontend-app
  PR #12: "Dashboard redesign" — ❌ CI failed (lint)
    → Spawning CI Fix Agent...

No other active PRs.
```
