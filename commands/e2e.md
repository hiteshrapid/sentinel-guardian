---
description: Generate and run end-to-end tests for critical business flows — API workflows or browser flows.
---

# /e2e

Usage: `/e2e [flow-description]`

## What it does
1. Detects whether to use API E2E or Browser E2E based on the project
2. Identifies critical business flows (or uses provided description)
3. Writes multi-step test scenarios
4. Runs tests against the deployed service
5. Reports results

## Skills Used
- **API E2E:** `e2e-api-tests` — multi-step httpx workflows against live URL
- **Browser E2E:** `e2e-browser-tests` — Playwright browser automation 

## Example — API E2E
```
/e2e Test the campaign creation and activation flow

🔗 Mode: API E2E (no frontend detected)
📝 Writing flow: test_campaign_lifecycle.py
   Step 1: Create campaign (draft)
   Step 2: Add customers
   Step 3: Activate campaign
   Step 4: Verify scheduler called
   Step 5: Deactivate
   Step 6: Cleanup
▶️  Running against E2E_BASE_URL...

✅ E2E Results:
  6 steps, 6 passed, 0 failed
  Duration: 4.1s
```
