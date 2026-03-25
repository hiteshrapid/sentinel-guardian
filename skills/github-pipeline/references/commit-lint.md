# commit-lint.yml — Commit Message Validator

**Customization point**: The `PATTERN` should match the user's Jira project keys AND conventional commit prefixes. Default accepts both Jira tickets (`RP-12 message`) and conventional commits (`feat: message`, `fix(scope): message`).

**Lesson learned**: Don't restrict to only Jira tickets — always also accept conventional commits (`feat`, `fix`, `chore`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `revert`). CI bots, automated tools, and quick fixes often use conventional commits. Blocking them creates unnecessary friction.

```yaml
name: Commit Message Lint

# Called by main.yml. Not triggered directly.
# Validates every commit starts with a Jira ticket ID or a release tag.
# Valid:   RP-12 Completed Auth  |  [QA Release] March batch  |  [Prod Release] v1.2
# Valid:   feat: add user export  |  fix(auth): token refresh  |  chore(ci): update deps
# Skips merge commits and revert commits automatically.

on:
  workflow_call:

jobs:
  lint-commits:
    name: Validate Commit Messages
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Resolve commit range
        id: range
        run: |
          if [ -n "${{ github.event.pull_request.base.sha }}" ]; then
            echo "base=${{ github.event.pull_request.base.sha }}" >> $GITHUB_OUTPUT
            echo "head=${{ github.event.pull_request.head.sha }}" >> $GITHUB_OUTPUT
          elif [ -n "${{ github.event.before }}" ] && \
               [ "${{ github.event.before }}" != "0000000000000000000000000000000000000000" ]; then
            echo "base=${{ github.event.before }}" >> $GITHUB_OUTPUT
            echo "head=${{ github.event.after }}" >> $GITHUB_OUTPUT
          else
            echo "skip=true" >> $GITHUB_OUTPUT
          fi

      - name: Validate Commit Messages
        if: steps.range.outputs.skip != 'true'
        run: |
          BASE="${{ steps.range.outputs.base }}"
          HEAD="${{ steps.range.outputs.head }}"
          PATTERN='^([A-Z]+-[0-9]+|\[QA Release\]|\[Prod Release\]|(feat|fix|chore|docs|style|refactor|perf|test|build|ci|revert)(\(.*\))?[!]?:)'

          echo "Checking commits from $BASE to $HEAD"
          echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

          FAILED=0
          TOTAL=0

          while IFS= read -r line; do
            SHA=$(echo "$line" | awk '{print $1}')
            MSG=$(echo "$line" | cut -d' ' -f2-)
            TOTAL=$((TOTAL + 1))

            if echo "$MSG" | grep -qE "^Merge (pull request|branch|remote)"; then
              echo "⏭️  SKIP   $SHA — $MSG (merge commit)"
              continue
            fi

            if echo "$MSG" | grep -qE '^Revert "'; then
              echo "⏭️  SKIP   $SHA — $MSG (revert commit)"
              continue
            fi

            if echo "$MSG" | grep -qE "$PATTERN"; then
              echo "✅  PASS   $SHA — $MSG"
            else
              echo "❌  FAIL   $SHA — $MSG"
              echo "           Expected: TICKET-123 message  |  feat: message  |  fix(scope): message  |  [QA Release] message"
              FAILED=$((FAILED + 1))
            fi

          done < <(git log "$BASE..$HEAD" --pretty=format:"%h %s")

          echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
          echo "Total: $TOTAL | Failed: $FAILED"

          if [ "$FAILED" -gt 0 ]; then
            echo "❌ $FAILED commit(s) failed. Fix the commit messages and try again."
            exit 1
          fi

          echo "✅ All commits follow the required format."

      - name: Skip
        if: steps.range.outputs.skip == 'true'
        run: echo "No commit range available (first push or manual trigger) — skipping."
```
