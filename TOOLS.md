# TOOLS.md — Sentinel Tooling

## Core Tools

### GitHub CLI (`gh`)
Already installed. Used for: PR management, CI status, issue tracking, code review.

### Claude Code (`claude`)
Available via coding-agent skill. Spawn with:
```
claude --permission-mode bypassPermissions --print "task"
```
Use for: writing tests, fixing failures, code analysis.

### Codex (`codex`)
Available via coding-agent skill. Spawn with PTY:
```
codex exec --full-auto "task"
```
Use for: alternative to Claude Code, parallel agent work.

## Test Frameworks

### Python
- **pytest** — primary test runner
- **pytest-asyncio** — async test support
- **pytest-cov** — coverage reporting
- **httpx** — async HTTP client for API testing
- **mongomock-motor** — MongoDB mocking for unit tests
- **testcontainers** — real DB containers for integration tests
- **factory-boy** — test data factories

### Browser / E2E
- **Playwright** — browser automation and E2E testing
- **pytest-playwright** — Playwright + pytest integration

### Security
- **pip-audit** — dependency vulnerability scanning
- **bandit** — static security analysis


### Jira API
For creating tickets and reading board state.

**Configuration (env vars in `/home/hitesh/.openclaw/.env`):**
- `JIRA_BASE_URL` = `https://ruh-ai-team.atlassian.net`
- `JIRA_EMAIL` = `hitesh@ruh.ai`
- `JIRA_API_TOKEN` = set in `.env` (API token from id.atlassian.com)

**Constants:**
- Default project: **TT** (Tech Tasks)
- Board ID: **438**
- Hitesh's account ID (assignee): `712020:cdec0682-ca29-4440-8aa1-55f17430917a`

**Create ticket example:**
```bash
curl -s -X POST \
  -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "fields": {
      "project": {"key": "TT"},
      "summary": "Sentinel: Bootstrap testing for repo-name",
      "issuetype": {"name": "Task"},
      "assignee": {"accountId": "712020:cdec0682-ca29-4440-8aa1-55f17430917a"}
    }
  }' \
  "$JIRA_BASE_URL/rest/api/3/issue"
```

**Used by:**
- Sentinel to create TT tickets before starting work
- `jira-transition.yml` to auto-transition tickets after deploy
- Heartbeat to link fix branches to tickets

## CI/CD
- **GitHub Actions** — primary CI platform (via `gh` CLI)
- Workflow templates in `templates/ci-workflows/`

## Stack Detection
- `scripts/detect-stack.sh` — auto-detect framework, DB, auth pattern
- Outputs: JSON with stack info for agent consumption

## APIs
- GitHub: ✅ via `gh` CLI
- Jira: TBD (credentials)

## Jira API

Sentinel creates tickets and reads ticket status via the Jira REST API.

**Required env vars (from GitHub Secrets or local config):**
- `JIRA_BASE_URL` — e.g. `https://yourcompany.atlassian.net`
- `JIRA_EMAIL` — CI bot email for API auth
- `JIRA_API_TOKEN` — from id.atlassian.com > Security > API tokens

**Usage:**
```bash
# Create a ticket on the TT board
curl -s -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"fields":{"project":{"key":"TT"},"summary":"Sentinel: bootstrap repo-name","issuetype":{"name":"Task"}}}' \
  "$JIRA_BASE_URL/rest/api/3/issue"

# Get ticket transitions
curl -s -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  "$JIRA_BASE_URL/rest/api/3/issue/TT-123/transitions"
```

Jira transitions are automated via `jira-transition.yml` in the canonical pipeline (see `github-pipeline` skill).
