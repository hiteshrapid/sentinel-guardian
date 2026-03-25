# HEARTBEAT.md — Sentinel Autonomous Monitoring

## Purpose

Every heartbeat: check repos, check PRs, check CI, take action or report. No fluff.

---

## Checklist (run every heartbeat)

### 1. PR Watch (HIGHEST PRIORITY)
```bash
# For each connected Tier 1 repo:
gh pr list --repo $REPO --state open --json number,title,reviewDecision,statusCheckRollup,comments
```
- New review comments? → Read them, address code changes, reply
- CI failing on PR? → Diagnose root cause, fix, push
- Requested changes? → Implement them
- Stale PR (>3 days no activity)? → Ping Hitesh

### 2. Team PR Review (DEFENSIVE MODE)
```bash
# Check for unreviewed team PRs on Tier 1 repos
gh pr list --repo $REPO --state open --json number,title,author,reviews,changedFiles
```
- For each PR NOT authored by Sentinel:
  - Already reviewed by Sentinel? → Check `memory/reviewed-prs.json`, skip if done
  - Not reviewed? → Pull diff, run review checklist:
    1. Coverage impact (does it drop below 100%?)
    2. Security scan (new endpoints without auth? hardcoded secrets?)
    3. Breaking changes (API schema changes without contract test updates?)
    4. Test quality (meaningful asserts? proper mocks?)
    5. Pattern enforcement (following repo conventions?)
  - Post PR review comment with P1/P2/P3 findings
  - Track in `memory/reviewed-prs.json`: `{"repo/PR#": {"reviewed": timestamp, "findings": count}}`
- Team pushed fixes after Sentinel review? → Re-review to verify fixes

### 3. CI Watch
```bash
# Check latest CI runs across Tier 1 repos
gh run list --repo $REPO --limit 3 --json conclusion,name,createdAt
```
- Any failures? → Classify root cause, create TT ticket, start fix or report
- PR without tests touching source? → Flag it

### 3. Nightly Regression Results (morning check)
```bash
gh run list --repo $REPO --workflow="Nightly Regression" --limit 1 --json conclusion
```
- Failed? → Diagnose, open fix branch, notify Hitesh
- Passed? → HEARTBEAT_OK for this repo

### 4. Coverage Watch
- Coverage dropped below 100%? → Alert + identify what changed
- New skip/xfail without reason? → Flag as test debt

### 5. Dependency Audit (weekly only)
```bash
# Python
pip-audit 2>&1 | grep -i "critical\|high"
# Node
npm audit --audit-level=high
```
- High/critical CVE? → Alert Hitesh immediately

---
### 6. Pipeline Compliance Check
```bash
# For each connected Tier 1+2 repo, verify canonical workflows exist
CANONICAL_WORKFLOWS=(ci.yml post-deploy.yml regression.yml)
# Also check for: ci-push.yml, commit-lint.yml, build-deploy.yml, jira-transition.yml
# (these may be called by or embedded in ci.yml depending on the repo)
for REPO in ruh-ai/sdr-backend ruh-ai/inbox-rotation-service ruh-ai/sdr-management-mcp ruh-ai/ruh-ai-admin-service ruh-ai/ruh-super-admin-fe; do
  WORKFLOWS=$(gh api repos/$REPO/contents/.github/workflows --jq '.[].name' 2>/dev/null)
  echo "$REPO: $WORKFLOWS"
done
```
- Missing canonical workflows? -> Flag for next bootstrap/update
- Present but outdated (missing SAST, missing DAST, wrong job names)? -> Flag as tech debt

---

## Connected Repos

| Repo | Branch | Tier | Pipeline | Status |
|------|--------|------|----------|--------|
| ruh-ai/sdr-backend | `dev` | P1 | ci + regression + post-deploy (3/7) | ✅ Bootstrapped — 2821 tests, 100% cov. ❌ Nightly regression failing (smoke env vars) |
| ruh-ai/inbox-rotation-service | `dev` | P1 | ci + regression + post-deploy (3/7) | ✅ Bootstrapped — 2220 tests, 100% cov. PR #57 merged |
| ruh-ai/sdr-management-mcp | `dev` | P2 | ci + regression + post-deploy (3/7) | ✅ Bootstrapped — 914 tests, 100% cov. PR #40 merged |
| ruh-ai/ruh-ai-admin-service | `dev` | P2 | ci (1/7) | 🔧 Bootstrap in progress — CI canonical branch exists |
| ruh-ai/ruh-super-admin-fe | `dev` | P1 | ci + post-deploy + regression (3/7) | ✅ PR #139 ALL GREEN — 130 test files, 1632 tests, 46 E2E; SAST+DAST added |
| ruh-ai/ruh-app-fe | `dev` | P1 | 0/7 | 🔲 Not started — deploy only, zero test CI |
| ruh-ai/ruh-ai-api-gateway | `dev` | P1 | 0/7 | 🔲 Not started — deploy only, zero test CI |

---

## Response Format

Nothing to do:
```
HEARTBEAT_OK
```

PRs need attention:
```
⚠️ ruh-ai/sdr-backend PR #XX — unresolved review comments
   → Addressing code review feedback
```

CI broken:
```
❌ ruh-ai/repo-name CI failed on PR #XX
   Root cause: [identified cause]
   Action: fixing on branch, push incoming
```

Regression failed:
```
❌ ruh-ai/repo-name nightly regression failed
   Job: [failing job]
   Root cause: [classification]
   Action: fix branch opened
```

---

## Post-Action Gate: Learnings

### When to Write
- You fixed a CI failure → write what broke and the fix pattern
- You responded to a PR review → write what the reviewer caught and why
- You wrote or modified tests → write what pattern worked or failed
- You triaged a regression → write the root cause classification
- HEARTBEAT_OK (no action) → do NOT write anything

### Format
```markdown
## {date} — Heartbeat: {repo-name} — {action summary}

**What happened:** {1-2 sentences}
**Root cause:** {classification}
**Fix applied:** {what you did}
**Learning:** {what to do differently or remember next time}
```

### Example
```markdown
## {date} — Heartbeat: {repo-name} — CI fix

**What happened:** Integration tests failed — container startup timeout.
**Root cause:** CI runner under heavy load, default timeout too aggressive.
**Fix applied:** Increased container startup timeout from 30s to 60s.
**Learning:** Default timeout (30s) is too aggressive for shared CI runners. Use 60s minimum.
```

### Gate Rule
If you took action but did NOT append to LEARNINGS.md, the heartbeat is INCOMPLETE. Do not report HEARTBEAT_OK or any status until the learning is written.
