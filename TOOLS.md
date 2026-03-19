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

## CI/CD
- **GitHub Actions** — primary CI platform (via `gh` CLI)
- Workflow templates in `templates/ci-workflows/`

## Stack Detection
- `scripts/detect-stack.sh` — auto-detect framework, DB, auth pattern
- Outputs: JSON with stack info for agent consumption

## APIs
- GitHub: ✅ via `gh` CLI
- Jira: TBD (credentials)
