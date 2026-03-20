---
name: unit-tests
description: >
  Implement production-ready unit tests for a backend application. Use this skill when
  the user wants to write unit tests for a backend service, test business logic in isolation,
  mock repositories or external dependencies with pytest-mock or unittest.mock, enforce coverage
  thresholds, or verify error handling in service classes. Trigger when the user mentions
  "unit tests for Python", "test my service layer", "mock my repository", "pytest setup",
  "test business logic Python", "pytest-mock", "coverage threshold", or "unit test my Python
  monolith". Always use this skill before writing any unit test file for a backend application —
  it contains setup, patterns, and a mandatory verification checklist.
---

# Python Monolith — Unit Tests Skill

## Stack Adaptation

Before writing any tests, detect the project'"'"'s stack and load the matching context:

| Signal | Context File |
|--------|-------------|
| `from fastapi` + `beanie`/`motor` | `contexts/fastapi-beanie.md` |
| `from fastapi` + `sqlalchemy` | `contexts/fastapi-sqlalchemy.md` |
| `from flask` | `contexts/flask-sqlalchemy.md` |
| `from django` | `contexts/django-orm.md` |
| `package.json` + `next` + `prisma` | `contexts/nextjs-prisma.md` |

Read the context file FIRST. It tells you: package manager, test runner, auth pattern, ORM, DB setup for tests, and stack-specific code patterns.

If the stack doesn't match any context, analyze the repo and create a new context before proceeding.

---


You are an expert backend QA engineer. Your mission: set up and implement production-ready unit
tests for a backend application. Unit tests cover business logic only — all I/O (DB, HTTP, cache,
filesystem) is mocked.

**Unit tests answer: "Does my business logic behave correctly in isolation?"**
They do NOT test HTTP routing, DB queries, or real network calls — that is integration territory.

---

## Phase 1 — Audit the Repo

```bash
# Framework and existing tooling
python3 -c "
import importlib
for pkg in ['fastapi','flask','django','sqlalchemy','pytest','unittest']:
    try: m=importlib.import_module(pkg); print(f'FOUND: {pkg} @ {getattr(m,\"__version__\",\"?\")}')
    except ImportError: pass
"
find . -name "test_*.py" -o -name "*_test.py" | grep -v __pycache__ | head -20
ls -la tests/ 2>/dev/null || echo "No tests/ dir yet"
```

Determine:
- [ ] Framework: FastAPI / Flask / Django / other
- [ ] ORM: SQLAlchemy / Tortoise / Django ORM / raw SQL
- [ ] Existing test tooling (pytest vs unittest)
- [ ] Architecture: services/repositories, domain-driven, or flat

---

## Phase 2 — Install Dependencies

```bash
pip install \
  pytest \
  pytest-asyncio \
  pytest-cov \
  pytest-mock \
  factory-boy \
  faker
```

---

## Phase 3 — Configure pytest

```toml
# pyproject.toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
markers = ["unit: fast tests with no I/O"]
addopts = ["--strict-markers", "-ra", "--tb=short"]

[tool.coverage.run]
source = ["app", "src"]   # adjust to your source dir
omit = ["*/tests/*", "*/migrations/*", "*/alembic/*"]
branch = true

[tool.coverage.report]
fail_under = 100
show_missing = true
```

**Makefile:**
```makefile
test-unit:
	pytest -m unit --cov --cov-report=term-missing

test-unit-watch:
	ptw -- -m unit
```

---

## Phase 4 — File Structure

```
tests/
└── unit/
    ├── test_user_service.py      ← one file per service/domain class
    ├── test_order_service.py
    ├── test_formatters.py        ← pure utility functions
    └── test_auth_middleware.py
```

**Naming convention:**
- Test files: `test_<module>.py`
- Test classes: `TestUserService`, `TestOrderService`
- Test functions: `test_<method>_<scenario>`

---

## Phase 5 — Write Unit Tests

### Pattern A — Service with Repository Dependency (async)

```python
# tests/unit/test_user_service.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pytest_mock import MockerFixture

# from app.services.user_service import UserService
# from app.repositories.user_repository import UserRepository
# from app.exceptions import ConflictError, NotFoundError, ValidationError


class TestUserService:
    """Unit tests for UserService — all I/O is mocked."""

    def setup_method(self):
        """Create a fresh mock repo and service before each test."""
        self.mock_repo = AsyncMock()
        # self.service = UserService(self.mock_repo)

    # ✅ Happy path
    @pytest.mark.unit
    async def test_create_user_returns_without_password(self):
        self.mock_repo.find_by_email.return_value = None
        self.mock_repo.create.return_value = {
            "id": "u1", "email": "alice@example.com", "created_at": "2024-01-01"
        }
        # result = await self.service.create_user(email="alice@example.com", password="Secure123!")
        # assert result["id"] == "u1"
        # assert "password" not in result

    # 🔒 Security: password must be hashed
    @pytest.mark.unit
    async def test_create_user_never_stores_plaintext_password(self):
        self.mock_repo.find_by_email.return_value = None
        self.mock_repo.create.return_value = {"id": "u1", "email": "a@b.com"}
        # await self.service.create_user(email="a@b.com", password="plaintext")
        # stored = self.mock_repo.create.call_args[1]["hashed_password"]
        # assert stored != "plaintext"
        # assert stored.startswith("$2b$")   # bcrypt format

    # ❌ Conflict
    @pytest.mark.unit
    async def test_create_user_raises_conflict_when_email_exists(self):
        self.mock_repo.find_by_email.return_value = {"id": "u1", "email": "a@b.com"}
        # with pytest.raises(ConflictError, match="already exists"):
        #     await self.service.create_user(email="a@b.com", password="x")

    # 🔲 Normalization
    @pytest.mark.unit
    async def test_create_user_normalizes_email_to_lowercase(self):
        self.mock_repo.find_by_email.return_value = None
        self.mock_repo.create.return_value = {"id": "u1", "email": "alice@example.com"}
        # await self.service.create_user(email="ALICE@EXAMPLE.COM", password="x")
        # called_with = self.mock_repo.create.call_args[1]
        # assert called_with["email"] == "alice@example.com"

    # 🔲 Edge case: empty input
    @pytest.mark.unit
    async def test_create_user_raises_validation_error_for_empty_email(self):
        # with pytest.raises(ValidationError):
        #     await self.service.create_user(email="", password="x")
        pass

    # 🔲 Not found
    @pytest.mark.unit
    async def test_get_user_raises_not_found_for_unknown_id(self):
        self.mock_repo.find_by_id.return_value = None
        # with pytest.raises(NotFoundError):
        #     await self.service.get_user_by_id("nonexistent-id")

    @pytest.mark.unit
    async def test_get_user_returns_user_when_found(self):
        self.mock_repo.find_by_id.return_value = {"id": "u1", "email": "a@b.com"}
        # result = await self.service.get_user_by_id("u1")
        # assert result["id"] == "u1"
```

### Pattern B — Pure Utility Functions

```python
# tests/unit/test_formatters.py
import pytest
# from app.utils.formatters import format_currency, slugify


class TestFormatCurrency:
    @pytest.mark.unit
    def test_formats_positive_amount(self):
        # assert format_currency(1234.56) == "$1,234.56"
        pass

    @pytest.mark.unit
    def test_formats_zero(self):
        # assert format_currency(0) == "$0.00"
        pass

    @pytest.mark.unit
    def test_rounds_to_two_decimal_places(self):
        # assert format_currency(1.999) == "$2.00"
        pass


class TestSlugify:
    @pytest.mark.unit
    def test_lowercases_and_hyphenates(self):
        # assert slugify("Hello World") == "hello-world"
        pass

    @pytest.mark.unit
    def test_removes_special_characters(self):
        # assert slugify("Hello, World!") == "hello-world"
        pass

    @pytest.mark.unit
    def test_handles_empty_string(self):
        # assert slugify("") == ""
        pass
```

### Pattern C — JWT Auth Logic

```python
# tests/unit/test_auth.py
import pytest
from datetime import timedelta
# from app.auth import verify_jwt, create_access_token
# from app.exceptions import ExpiredTokenError, InvalidTokenError

TEST_SECRET = "test-secret-123"


class TestVerifyJwt:
    @pytest.mark.unit
    def test_returns_payload_for_valid_token(self):
        # token = create_access_token({"sub": "u1"}, secret=TEST_SECRET)
        # payload = verify_jwt(token, secret=TEST_SECRET)
        # assert payload["sub"] == "u1"
        pass

    @pytest.mark.unit
    def test_raises_for_expired_token(self):
        # token = create_access_token({"sub": "u1"}, secret=TEST_SECRET, expires_delta=timedelta(seconds=-1))
        # with pytest.raises(ExpiredTokenError):
        #     verify_jwt(token, secret=TEST_SECRET)
        pass

    @pytest.mark.unit
    def test_raises_for_wrong_secret(self):
        # token = create_access_token({"sub": "u1"}, secret="wrong")
        # with pytest.raises(InvalidTokenError):
        #     verify_jwt(token, secret=TEST_SECRET)
        pass

    @pytest.mark.unit
    def test_raises_for_malformed_token(self):
        # with pytest.raises(InvalidTokenError):
        #     verify_jwt("not.a.valid.token", secret=TEST_SECRET)
        pass
```

### Pattern D — Sync Service (Flask / Django)

```python
# tests/unit/test_payment_service.py
import pytest
from unittest.mock import MagicMock, patch
# from app.services.payment_service import PaymentService
# from app.exceptions import PaymentError


class TestPaymentService:
    def setup_method(self):
        self.mock_gateway = MagicMock()
        # self.service = PaymentService(payment_gateway=self.mock_gateway)

    @pytest.mark.unit
    def test_charge_calls_gateway_with_correct_amount(self):
        self.mock_gateway.charge.return_value = {"status": "success", "charge_id": "ch_123"}
        # result = self.service.charge(user_id="u1", amount_cents=1000)
        # self.mock_gateway.charge.assert_called_once_with(amount=1000, currency="usd")
        # assert result["charge_id"] == "ch_123"
        pass

    @pytest.mark.unit
    def test_charge_raises_payment_error_on_gateway_failure(self):
        self.mock_gateway.charge.side_effect = Exception("Card declined")
        # with pytest.raises(PaymentError, match="Card declined"):
        #     self.service.charge(user_id="u1", amount_cents=1000)
        pass
```

---


## Phase 6 — Required Test Scenarios Per Service

| Scenario | Required |
|---|---|
| Happy path (success) | ✅ per public method |
| Input validation error | ✅ per validated param |
| Not found error | ✅ per method that fetches by ID |
| Conflict / duplicate | ✅ per unique constraint |
| Security: no plaintext secrets stored | ✅ auth/payment services |
| Edge case: None/empty inputs | ✅ per required param |
| Data normalization (lowercase, strip) | ✅ when applicable |
| Repository called with correct args | ✅ per write operation |

---

## Phase 7 — Verification Gates

### GATE 1 — Test file exists for every service

```bash
echo "====== GATE 1: Unit Test File Coverage ======"
missing=0
for f in $(find app/services src/services -name "*.py" 2>/dev/null \
          | grep -v "__init__\|migrations\|test" | grep -v __pycache__); do
  module=$(basename "$f" .py)
  found=$(find tests/unit -name "test_${module}.py" 2>/dev/null | wc -l)
  [ "$found" -gt 0 ] && echo "  [OK] test_${module}.py" || { echo "  [MISSING] tests/unit/test_${module}.py"; missing=$((missing+1)); }
done
[ "$missing" -eq 0 ] && echo "  GATE 1: PASS" || echo "  GATE 1: FAIL — $missing files missing"
```

### GATE 2 — Scenario coverage

```bash
echo "====== GATE 2: Scenario Coverage ======"
errors=$(grep -r "pytest.raises\|assertRaises" tests/unit/ 2>/dev/null | wc -l)
[ "$errors" -ge 3 ] && echo "  [PASS] Error paths: $errors" || echo "  [FAIL] Add NOT_FOUND, CONFLICT, VALIDATION error tests"

mocks=$(grep -r "AsyncMock\|MagicMock\|mock_repo\|mocker\." tests/unit/ 2>/dev/null | wc -l)
[ "$mocks" -ge 1 ] && echo "  [PASS] Mocking present: $mocks" || echo "  [FAIL] No mocking — unit tests must mock all I/O"

real_io=$(grep -rn "asyncpg\|psycopg2\|httpx\." tests/unit/ 2>/dev/null | grep -v "Mock\|mock")
[ -z "$real_io" ] && echo "  [PASS] No real I/O in unit tests" || echo "  [FAIL] Real I/O found — mock it: $real_io"
```

### GATE 3 — All tests pass + coverage met

```bash
echo "====== GATE 3 & 4: Execution + Coverage ======"
pytest -m unit --cov --cov-report=term-missing 2>&1 | tail -8
[ $? -eq 0 ] && echo "  GATE 3+4: PASS" || echo "  GATE 3+4: FAIL"
```

### GATE 4 — No test debt

```bash
echo "====== GATE 4: Test Debt ======"
skips=$(grep -rn "pytest.mark.skip\|skipTest\|xfail" tests/unit/ 2>/dev/null)
[ -z "$skips" ] && echo "  GATE 4: PASS" || echo "  GATE 4: FAIL — $skips"
```

---

## What comes next

- **Integration tests** → use `integration-tests` skill
- **Contract tests** → use `contract-tests` skill

---

## Mandatory: Post-Write Review Gate

After writing tests, **before committing**, run the `test-review` skill:
- External service leak scan (every client in `utils/clients/` mocked in conftest)
- DB safety audit (no production defaults, stable IDs, db_manager restore)
- Duplication scan (no copy-pasted infrastructure across files)
- Mock target verification (patch paths match real source)
- Lint + format + combined suite run

No test changes ship without passing this gate.
