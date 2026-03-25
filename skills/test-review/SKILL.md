---
name: test-review
description: >
  Post-write quality review for test suites. Run AFTER writing or modifying tests to catch
  duplication, real service leaks, bad mocks, unsafe DB defaults, dead code, and structural
  problems. Trigger on: "review tests", "check test quality", "audit test suite", "deduplicate
  tests", "test review", "post-write check", or automatically after any test-writing phase
  completes. This is the mandatory final gate before committing test changes.
---

# Test Review Skill — Post-Write Quality Gate

Run this **after every test-writing phase** and **before committing**. No exceptions.

---

## When to Trigger

- After any agent writes or modifies test files
- After coverage push or test bootstrap
- Before opening a PR with test changes
- On `/review-tests` command

---

## Review Checklist (execute in order)

### 1. External Service Leak Scan

**No test may call a real external service — not even constructors.**

```bash
# Find all external client classes in source
grep -rn "class.*Client\|class.*Api\b" <source_dir>/utils/clients/ --include="*.py" | grep -v __pycache__

# For each client, verify it's mocked in the appropriate conftest
for client in AgentClient SchedulerApi TriggerApi InboxRotationApi PDLClient ApolloClient GCSClient RedisClient OrganisationClient MCPClient ApiGatewayClient AgentGatewayClient; do
  echo -n "$client: "
  grep -rn "$client" tests/integration/conftest.py tests/performance/conftest.py 2>/dev/null | head -1 || echo "⚠️  NOT MOCKED IN CONFTEST"
done
```

**Fix pattern:** Add missing clients to `_mock_external_services` in the suite's `conftest.py`.

### 2. DB Safety Audit

```bash
# Check for production DB defaults
grep -rn "<production_db_name>" tests/ --include="*.py" | grep -v __pycache__

# Check for time-based IDs (orphan data on every run)
grep -rn "time.time()\|time()" tests/ --include="*.py" | grep -i "user_id\|mock_user\|test_user" | grep -v __pycache__

# Check for hardcoded production data
grep -rn "mongodb.net\|cluster0\|REAL_USER_ID\|REAL_CONVERSATION" tests/ --include="*.py" | grep -v __pycache__

# Verify db_manager restoration
grep -rn "db_manager.client\|db_manager.database" tests/ --include="*.py" | grep -v __pycache__
```

**Rules:**
- DB name must default to `test_*` — never production name
- User IDs must be stable — never `f"test_user_{int(time.time())}"`
- `db_manager` singleton must be saved/restored after tests
- Production URI guard must exist

### 3. Duplication Scan

```bash
# Find duplicate fixture/helper blocks across files
for pattern in "def _try_real_mongodb" "def _make_client" "def _ensure_user" "def _ensure_campaign" "def _mock_external_services"; do
  count=$(grep -rn "$pattern" tests/ --include="*.py" | grep -v __pycache__ | wc -l)
  if [ "$count" -gt 1 ]; then
    echo "⚠️  DUPLICATED ($count×): $pattern"
    grep -rn "$pattern" tests/ --include="*.py" | grep -v __pycache__
  fi
done

# Find test files >400 lines (candidates for splitting)
find tests/ -name "test_*.py" -exec wc -l {} + | sort -rn | head -10
```

**Rules:**
- Infrastructure code (DB setup, mocks, client creation) lives in `conftest.py` only
- Helper functions shared across 2+ files → extract to `conftest.py` or `tests/helpers/`
- No copy-pasting fixture blocks between files

### 4. Mock Target Verification

```bash
# Extract all patch targets from tests
grep -rn 'patch("' tests/ --include="*.py" | grep -v __pycache__ | \
  sed 's/.*patch("\([^"]*\)".*/\1/' | sort -u | while read target; do
    # Convert patch path to file path
    module_path=$(echo "$target" | sed 's/\./\//g' | sed 's/\/[^/]*$//')
    method=$(echo "$target" | sed 's/.*\.//')
    # Check if the method exists
    if [ -f "${module_path}.py" ]; then
      if ! grep -q "def $method\|$method\s*=" "${module_path}.py" 2>/dev/null; then
        if ! grep -q "class $method" "${module_path}.py" 2>/dev/null; then
          echo "⚠️  MOCK TARGET NOT FOUND: $target"
        fi
      fi
    fi
  done
```

### 5. Lint + Format Check

```bash
uv run ruff check tests/ --output-format=concise
uv run ruff format tests/ --check
```

### 6. Test Isolation Verification

```bash
# Run full combined suite (catches cross-suite pollution)
uv run pytest tests/unit/ tests/integration/ tests/contract/ tests/security/ tests/smoke/ -q --tb=line
```

If combined run fails but individual suites pass → test isolation issue (env vars, singleton state, import side effects).

### 7. Coverage Sanity Check

```bash
# Verify no catch-all test files exist
find tests/ -name "test_final*.py" -o -name "test_remaining*.py" -o -name "test_100pct*.py" | head -5

# Verify tests are source-aligned
ls tests/unit/ | sed 's/test_//' | sed 's/.py//' | sort > /tmp/test_modules.txt
ls <source_dir>/**/*.py | sed 's/.*\///' | sed 's/.py//' | sort > /tmp/source_modules.txt
# Unmatched test files may be catch-alls in disguise
```

---

## Output Format

```
## Test Review Results

### External Service Leaks
✅ All clients mocked in conftest — OR — ❌ Missing: [list]

### DB Safety
✅ No production defaults — OR — ❌ Issues: [list]

### Duplication
✅ No infrastructure duplication — OR — ❌ Duplicated: [list]

### Mock Targets
✅ All patch targets verified — OR — ⚠️ Unverified: [list]

### Lint + Format
✅ Clean — OR — ❌ [count] errors

### Test Isolation
✅ Combined suite green — OR — ❌ [count] failures in combined run

### Action Items
1. [specific fix needed]
2. [specific fix needed]
```

---

## Integration with Agent Pipeline

This skill is the **mandatory final gate** in the test pipeline:

```
Write tests → Run tests → REVIEW TESTS (this skill) → Commit → PR
```

No test changes should be committed without passing this review.
