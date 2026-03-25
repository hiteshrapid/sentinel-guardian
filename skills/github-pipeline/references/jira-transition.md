# jira-transition.yml — Jira Ticket Auto-Transition

**Customization points**:
1. `grep -oE '(RP|TT|SDR|ES)-[0-9]+'` — replace project keys with the user's own Jira project keys
2. Transition names in the `target` step — must exactly match transition names in the user's Jira workflow (case-insensitive match is used)

```yaml
name: Jira Ticket Transition
run-name: >-
  Jira Ticket Transition
  (${{ contains(github.event.workflow_run.name, '(main)') && 'main'
    || contains(github.event.workflow_run.name, '(qa)') && 'qa'
    || 'dev' }})

# Workflow 4 — Triggered automatically when Post-Deploy Tests succeed on dev, qa, or main.
# Transitions Jira tickets based on which branch was deployed to:
#   dev  → Ready to Deploy - QA
#   qa   → IN QA
#   main → RELEASED TO PROD
# Supported boards: RP, TT, SDR, ES
#
# ── Secrets required ──────────────────────────────────────────────────────────
# JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN

on:
  workflow_run:
    workflows: ["Post-Deploy Tests"]
    types: [completed]
    branches: [dev, qa, main]

env:
  FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: "true"

jobs:
  transition-jira:
    runs-on: ubuntu-latest
    if: github.event.workflow_run.conclusion == 'success'
    permissions:
      pull-requests: read

    steps:
      - name: Determine target transition
        id: target
        env:
          # github.event.workflow_run.head_branch is unreliable for chained workflow_run workflows.
          # Resolve the real branch from the upstream run name e.g. "Post-Deploy Tests (qa)".
          UPSTREAM_RUN_NAME: ${{ github.event.workflow_run.name }}
        run: |
          BRANCH=$(echo "$UPSTREAM_RUN_NAME" | grep -oE '\((dev|qa|main)\)' | tr -d '()')
          if [ "$BRANCH" = "dev" ]; then
            echo "transition_name=Ready to Deploy - QA" >> $GITHUB_OUTPUT
          elif [ "$BRANCH" = "qa" ]; then
            echo "transition_name=IN QA" >> $GITHUB_OUTPUT
          elif [ "$BRANCH" = "main" ]; then
            echo "transition_name=RELEASED TO PROD" >> $GITHUB_OUTPUT
          else
            echo "Branch '$BRANCH' (from '$UPSTREAM_RUN_NAME') has no mapped transition — skipping"
            echo "skip=true" >> $GITHUB_OUTPUT
          fi

      - name: Extract Ticket IDs from merged PR
        if: steps.target.outputs.skip != 'true'
        id: extract
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          COMMIT_SHA: ${{ github.event.workflow_run.head_sha }}
          UPSTREAM_RUN_NAME: ${{ github.event.workflow_run.name }}
          REPO: ${{ github.repository }}
        run: |
          PR_DATA=$(gh api "repos/$REPO/commits/$COMMIT_SHA/pulls" \
            -H "Accept: application/vnd.github+json" 2>/dev/null || echo "[]")

          TITLE=$(echo "$PR_DATA" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d[0]['title'] if d else '')" 2>/dev/null || echo "")
          BODY=$(echo "$PR_DATA" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d[0]['body'] or '' if d else '')" 2>/dev/null || echo "")
          PR_NUMBER=$(echo "$PR_DATA" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d[0]['number'] if d else '')" 2>/dev/null || echo "")
          PR_URL=$(echo "$PR_DATA" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d[0]['html_url'] if d else '')" 2>/dev/null || echo "")
          MERGED_BY=$(echo "$PR_DATA" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d[0]['merged_by']['login'] if d and d[0].get('merged_by') else '')" 2>/dev/null || echo "")

          BRANCH=$(echo "$UPSTREAM_RUN_NAME" | grep -oE '\((dev|qa|main)\)' | tr -d '()')
          ALL_TEXT="$BRANCH $TITLE $BODY"
          TICKET_IDS=$(echo "$ALL_TEXT" | grep -oE '(RP|TT|SDR|ES)-[0-9]+' | sort -u | tr '\n' ' ')

          if [ -z "$TICKET_IDS" ]; then
            echo "No ticket IDs found — skipping"
            echo "found=false" >> $GITHUB_OUTPUT
          else
            echo "Found ticket IDs: $TICKET_IDS"
            echo "ticket_ids=$TICKET_IDS" >> $GITHUB_OUTPUT
            echo "pr_number=$PR_NUMBER" >> $GITHUB_OUTPUT
            echo "pr_url=$PR_URL" >> $GITHUB_OUTPUT
            echo "merged_by=$MERGED_BY" >> $GITHUB_OUTPUT
            echo "found=true" >> $GITHUB_OUTPUT
          fi

      - name: Get Transition ID
        if: steps.extract.outputs.found == 'true'
        id: transition
        env:
          JIRA_BASE_URL: ${{ secrets.JIRA_BASE_URL }}
          JIRA_EMAIL: ${{ secrets.JIRA_EMAIL }}
          JIRA_API_TOKEN: ${{ secrets.JIRA_API_TOKEN }}
          TICKET_IDS: ${{ steps.extract.outputs.ticket_ids }}
          TRANSITION_NAME: ${{ steps.target.outputs.transition_name }}
        run: |
          FIRST_TICKET=$(echo "$TICKET_IDS" | awk '{print $1}')

          TRANSITIONS=$(curl -s \
            -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
            -H "Content-Type: application/json" \
            "$JIRA_BASE_URL/rest/api/3/issue/$FIRST_TICKET/transitions")

          TRANSITION_ID=$(echo "$TRANSITIONS" | python3 -c "
          import sys, json, os
          data = json.load(sys.stdin)
          target = os.environ['TRANSITION_NAME'].upper()
          for t in data.get('transitions', []):
              if t['name'].upper() == target:
                  print(t['id'])
                  break
          ")

          if [ -z "$TRANSITION_ID" ]; then
            echo "Could not find transition '$TRANSITION_NAME' — check status name in Jira"
            echo "found=false" >> $GITHUB_OUTPUT
          else
            echo "Transition ID for '$TRANSITION_NAME': $TRANSITION_ID"
            echo "transition_id=$TRANSITION_ID" >> $GITHUB_OUTPUT
            echo "found=true" >> $GITHUB_OUTPUT
          fi

      - name: Transition Tickets
        if: |
          steps.extract.outputs.found == 'true' &&
          steps.transition.outputs.found == 'true'
        env:
          JIRA_BASE_URL: ${{ secrets.JIRA_BASE_URL }}
          JIRA_EMAIL: ${{ secrets.JIRA_EMAIL }}
          JIRA_API_TOKEN: ${{ secrets.JIRA_API_TOKEN }}
          TICKET_IDS: ${{ steps.extract.outputs.ticket_ids }}
          TRANSITION_ID: ${{ steps.transition.outputs.transition_id }}
          TARGET: ${{ steps.target.outputs.transition_name }}
        run: |
          for TICKET in $TICKET_IDS; do
            RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" \
              -X POST \
              -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
              -H "Content-Type: application/json" \
              -d "{\"transition\": {\"id\": \"$TRANSITION_ID\"}}" \
              "$JIRA_BASE_URL/rest/api/3/issue/$TICKET/transitions")

            [ "$RESPONSE" == "204" ] && echo "✅ $TICKET → $TARGET" || echo "⚠️  $TICKET transition failed — HTTP $RESPONSE"
          done

      - name: Add Comment on Jira Ticket
        if: |
          steps.extract.outputs.found == 'true' &&
          steps.transition.outputs.found == 'true'
        env:
          JIRA_BASE_URL: ${{ secrets.JIRA_BASE_URL }}
          JIRA_EMAIL: ${{ secrets.JIRA_EMAIL }}
          JIRA_API_TOKEN: ${{ secrets.JIRA_API_TOKEN }}
          TICKET_IDS: ${{ steps.extract.outputs.ticket_ids }}
          PR_NUMBER: ${{ steps.extract.outputs.pr_number }}
          PR_URL: ${{ steps.extract.outputs.pr_url }}
          REPO: ${{ github.event.repository.name }}
          MERGED_BY: ${{ steps.extract.outputs.merged_by }}
          BRANCH: ${{ github.event.workflow_run.head_branch }}
          TARGET: ${{ steps.target.outputs.transition_name }}
        run: |
          for TICKET in $TICKET_IDS; do
            curl -s -o /dev/null \
              -X POST \
              -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
              -H "Content-Type: application/json" \
              -d "{
                \"body\": {
                  \"type\": \"doc\",
                  \"version\": 1,
                  \"content\": [{
                    \"type\": \"paragraph\",
                    \"content\": [{
                      \"type\": \"text\",
                      \"text\": \"✅ PR #$PR_NUMBER merged into $BRANCH in $REPO by @$MERGED_BY. Ticket transitioned to $TARGET. $PR_URL\"
                    }]
                  }]
                }
              }" \
              "$JIRA_BASE_URL/rest/api/3/issue/$TICKET/comment"

            echo "✅ Comment added to $TICKET"
          done
```
