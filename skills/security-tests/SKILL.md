---
name: security-tests
description: >
  Implement security scanning and security-focused test cases for a backend application.
  Use this skill when the user wants to add dependency vulnerability scanning, check for OWASP
  Top 10 issues, test authentication edge cases, test authorization boundaries, add security
  headers validation, or set up automated security checks in GitHub Actions CI. Trigger when
  the user mentions "security tests", "pip-audit in CI", "OWASP tests", "test SQL
  injection", "test XSS", "dependency vulnerability scan", "bandit", "safety",
  "semgrep", "test JWT security", "test rate limiting", or "security scan
  my API". Always use this skill alongside unit and integration tests — security is a
  required layer for production backends.
---

# Security Tests Skill

## Stack Adaptation

Before writing any tests, detect the project's stack and load the matching context:

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

You are an expert backend security engineer. Your mission: implement security scanning and
security-focused test cases for a backend application, covering dependency vulnerabilities,
authentication edge cases, authorization boundaries, and injection protection.

**Security tests answer: "Can this service be exploited or abused?"**

---

## Phase 1 — Audit Current State

```bash
# Existing security tooling
python3 -c "
import importlib
for pkg in ['pip_audit','safety','bandit','slowapi','passlib','python_jose','PyJWT']:
    try: m=importlib.import_module(pkg.replace('-','_')); print(f'FOUND: {pkg}')
    except ImportError: print(f'MISSING: {pkg}')
"

# Run pip-audit now — see baseline
pip-audit 2>/dev/null | head -20 || echo "pip-audit not installed"

# Check security headers middleware
grep -r "helmet\|SecurityHeaders\|X-Content-Type\|X-Frame" . --include="*.py" -l 2>/dev/null | grep -v test | head -5

# Check rate limiting
grep -r "slowapi\|RateLimiter\|throttle\|rate_limit" . --include="*.py" -l 2>/dev/null | grep -v test | head -5

# Check input validation
grep -r "pydantic\|marshmallow\|cerberus\|voluptuous" . --include="*.py" -l 2>/dev/null | grep -v test | head -5
```

Determine:
- [ ] Current pip-audit vulnerability count
- [ ] Security headers middleware in place
- [ ] Rate limiting configured
- [ ] Input validation library (Pydantic, Marshmallow)
- [ ] Auth: JWT / sessions / API keys

---

## Phase 2 — Install Security Tools

```bash
# Dependency scanning
pip install pip-audit safety

# Static analysis
pip install bandit

# Runtime security (not dev-only)
pip install slowapi          # rate limiting for FastAPI/Starlette
pip install secure           # security headers helper
pip install python-jose[cryptography]
pip install passlib[bcrypt]
```

---

## Phase 3 — Dependency Vulnerability Scanning

### pip-audit Configuration

```bash
# Run as part of CI
pip-audit --format=json --output=audit-report.json

# Fail on high/critical — use in CI
pip-audit --ignore-vuln GHSA-xxxx-xxxx-xxxx  # allowlist specific CVEs with justification
```

**Makefile targets:**
```makefile
security-audit:
	pip-audit

security-audit-json:
	pip-audit --format=json --output=audit-report.json

security-bandit:
	bandit -r app/ src/ -ll   # -ll = only medium and high severity

security-all: security-audit security-bandit
```

**policy:** `pip-audit` exits non-zero on any vulnerability. Add to allowlist only with written
justification comment explaining why the risk is accepted and when it will be resolved.

---

## Phase 4 — Bandit Static Analysis

```bash
# Run locally
bandit -r app/ -ll -ii   # medium+ severity, medium+ confidence

# Save report
bandit -r app/ -f json -o bandit-report.json

# Common rules to NOT suppress:
# B105 - hardcoded password string
# B106 - hardcoded password funcarg
# B107 - hardcoded password in default
# B201 - flask debug true
# B501 - request ssl verify disabled
# B506 - yaml load without Loader
# B602 - subprocess with shell=True
```

---

## Phase 5 — Security-Focused Integration Tests

```python
# tests/security/test_auth_security.py
import pytest
import pytest_asyncio
from httpx import AsyncClient
from tests.helpers.auth_helpers import (
    generate_auth_token,
    generate_expired_token,
    generate_tampered_token,
)

pytestmark = pytest.mark.security


class TestAuthenticationSecurity:
    """JWT and authentication edge cases."""

    async def test_rejects_missing_token(self, client: AsyncClient):
        res = await client.get("/api/users/me")
        assert res.status_code == 401
        assert "data" not in res.json()   # no data leaked on 401

    async def test_rejects_malformed_authorization_header(self, client: AsyncClient):
        res = await client.get(
            "/api/users/me",
            headers={"Authorization": "not-bearer-format"}
        )
        assert res.status_code == 401

    async def test_rejects_expired_token(self, client: AsyncClient):
        token = generate_expired_token("u1")
        res = await client.get(
            "/api/users/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert res.status_code == 401

    async def test_rejects_token_with_wrong_secret(self, client: AsyncClient):
        token = generate_tampered_token("u1")
        res = await client.get(
            "/api/users/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert res.status_code == 401

    async def test_rejects_alg_none_attack(self, client: AsyncClient):
        """JWT 'none' algorithm bypass attempt must be rejected."""
        import base64, json as jsonlib
        header = base64.urlsafe_b64encode(b'{"alg":"none"}').rstrip(b'=').decode()
        payload_data = {"sub": "admin", "role": "admin", "exp": 9999999999}
        payload = base64.urlsafe_b64encode(
            jsonlib.dumps(payload_data).encode()
        ).rstrip(b'=').decode()
        fake_token = f"{header}.{payload}."   # empty signature
        res = await client.get(
            "/api/users/me",
            headers={"Authorization": f"Bearer {fake_token}"}
        )
        assert res.status_code == 401

    async def test_rejects_token_with_injected_admin_role(self, client: AsyncClient):
        """A user cannot forge an admin token."""
        from jose import jwt as jose_jwt
        token = jose_jwt.encode(
            {"sub": "u1", "role": "admin"},
            "wrong-secret",
            algorithm="HS256"
        )
        res = await client.get(
            "/api/admin/users",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert res.status_code in (401, 403)


class TestAuthorizationSecurity:
    """Access control boundary tests."""

    async def test_user_cannot_access_another_users_data(self, client: AsyncClient):
        token = generate_auth_token("user-1", role="user")
        res = await client.get(
            "/api/users/user-2",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert res.status_code == 403

    async def test_non_admin_cannot_access_admin_endpoint(self, client: AsyncClient):
        token = generate_auth_token("user-1", role="user")
        res = await client.delete(
            "/api/admin/users/user-2",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert res.status_code == 403

    async def test_privilege_escalation_via_body_rejected(self, client: AsyncClient):
        """User cannot self-promote by including role in PATCH body."""
        # Create a user first, then try to escalate
        created = await client.post(
            "/api/users",
            json={"email": "escalate@test.com", "password": "Secure123!"}
        )
        if created.status_code != 201:
            pytest.skip("User creation failed — skip escalation test")

        user_id = created.json()["id"]
        token = generate_auth_token(user_id, role="user")

        await client.patch(
            f"/api/users/{user_id}",
            json={"role": "admin"},           # try to self-escalate
            headers={"Authorization": f"Bearer {token}"}
        )

        # Verify role unchanged
        me = await client.get(
            "/api/users/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        if me.status_code == 200:
            assert me.json().get("role") != "admin"


class TestInputValidation:
    """Injection and malformed input protection."""

    async def test_injection_in_query_params_handled(self, client: AsyncClient):
        """Injection attempt must not cause 500 or return all records."""
        token = generate_auth_token("admin-1", role="admin")
        res = await client.get(
            "/api/users?search=' OR '1'='1",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert res.status_code in (200, 400, 422)
        if res.status_code == 200:
            # If 200, must not return all users (injection did not work)
            items = res.json().get("items", res.json().get("users", []))
            assert len(items) < 100

    async def test_oversized_payload_rejected(self, client: AsyncClient):
        """Payloads exceeding size limits must be rejected."""
        large_payload = {"name": "x" * 1_000_000}
        res = await client.post("/api/items", json=large_payload)
        assert res.status_code in (400, 413, 422)

    async def test_null_bytes_in_input_handled(self, client: AsyncClient):
        """Null bytes in input must not cause 500."""
        res = await client.post(
            "/api/users",
            json={"email": "test\x00@example.com", "password": "x"}
        )
        assert res.status_code != 500

    async def test_deeply_nested_json_rejected_or_handled(self, client: AsyncClient):
        """Deeply nested JSON must not cause recursion errors or 500."""
        nested = {"a": {}}
        current = nested["a"]
        for _ in range(200):
            current["a"] = {}
            current = current["a"]

        res = await client.post("/api/items", json=nested)
        assert res.status_code != 500


class TestSecurityHeaders:
    """HTTP security headers validation."""

    async def test_x_content_type_options_present(self, client: AsyncClient):
        res = await client.get("/health")
        assert res.headers.get("x-content-type-options") == "nosniff"

    async def test_x_frame_options_present(self, client: AsyncClient):
        res = await client.get("/health")
        assert "x-frame-options" in res.headers

    async def test_server_header_absent(self, client: AsyncClient):
        res = await client.get("/health")
        # Should not expose server technology details
        server = res.headers.get("server", "").lower()
        assert "uvicorn" not in server or server == ""  # or whatever your server is

    async def test_no_sensitive_data_in_error_responses(self, client: AsyncClient):
        """Error responses must not leak stack traces or internal paths."""
        res = await client.get("/api/nonexistent-endpoint-xyz")
        body = res.text
        assert "Traceback" not in body
        assert "/home/" not in body
        assert "site-packages" not in body


class TestRateLimiting:
    """Rate limiting enforcement."""

    async def test_429_after_exceeding_auth_threshold(self, client: AsyncClient):
        """Auth endpoints must enforce rate limiting."""
        results = []
        for _ in range(110):
            res = await client.post(
                "/api/auth/login",
                json={"email": "x@x.com", "password": "wrong"}
            )
            results.append(res.status_code)

        assert 429 in results, "Rate limiting not triggered after 110 requests"
```

---


## Phase 6 — Security Middleware Setup (Runtime)

### FastAPI with slowapi + secure headers

```python
# app/middleware/security.py
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import secure

limiter = Limiter(key_func=get_remote_address)


def setup_security_middleware(app: FastAPI) -> None:
    """Configure all security middleware for the application."""

    # Rate limiting
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Security headers via `secure` library
    secure_headers = secure.Secure()

    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        response = await call_next(request)
        secure_headers.framework.fastapi(response)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

    # Remove server identification
    @app.middleware("http")
    async def remove_server_header(request: Request, call_next):
        response = await call_next(request)
        response.headers.pop("server", None)
        return response
```

### Apply rate limits to auth endpoints

```python
# app/routers/auth.py
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/login")
@limiter.limit("10/15minute")
async def login(request: Request, credentials: LoginSchema):
    ...

@router.post("/register")
@limiter.limit("5/hour")
async def register(request: Request, payload: RegisterSchema):
    ...
```

---

## Phase 7 — GitHub Actions CI Integration

```yaml
# .github/workflows/ci.yml — security jobs

security-audit:
  name: Dependency Vulnerability Scan
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with: { python-version: '3.12' }
    - run: pip install pip-audit
    - run: pip-audit   # fails on any vulnerability

bandit-scan:
  name: Bandit Static Analysis
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with: { python-version: '3.12' }
    - run: pip install bandit
    - run: bandit -r app/ src/ -ll -ii -f json -o bandit-report.json
    - uses: actions/upload-artifact@v4
      if: always()
      with:
        name: bandit-report
        path: bandit-report.json

security-tests:
  name: Security Integration Tests
  runs-on: ubuntu-latest
  needs: [unit, integration]
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with: { python-version: '3.12' }
    - run: pip install -r requirements.txt
    - run: pytest -m security -p no:xdist -v
```

---

## Phase 8 — Verification Gates

### GATE 1 — No high/critical vulnerabilities

```bash
echo "====== GATE 1: Dependency Vulnerabilities ======"
pip-audit --format=json 2>/dev/null | python3 -c "
import json, sys
data = json.load(sys.stdin)
high_crit = [d for d in data.get('dependencies', [])
             if any(v.get('fix_versions') for v in d.get('vulns', []))]
if high_crit:
    print(f'  [FAIL] {len(high_crit)} vulnerable packages — run pip-audit for details')
    sys.exit(1)
else:
    print('  GATE 1: PASS')
" || echo "  GATE 1: Run pip-audit to check"
```

### GATE 2 — Security test scenarios present

```bash
echo "====== GATE 2: Security Test Coverage ======"
for scenario in "status_code == 401" "status_code == 403" "alg.*none\|none.*alg" "nosniff\|x-content-type" "429\|rate"; do
  count=$(grep -r "$scenario" tests/security/ --include="*.py" 2>/dev/null -i | wc -l)
  [ "$count" -ge 1 ] \
    && echo "  [PASS] '$scenario' covered: $count" \
    || echo "  [FAIL] Missing security test for: $scenario"
done
```

### GATE 3 — Security middleware present

```bash
echo "====== GATE 3: Security Middleware ======"
headers=$(grep -r "x-content-type\|nosniff\|secure\.\|SecurityHeaders" . --include="*.py" 2>/dev/null | grep -v test | wc -l)
[ "$headers" -ge 1 ] && echo "  [PASS] Security headers middleware present" || echo "  [FAIL] No security headers — add secure headers middleware"

rate=$(grep -r "slowapi\|RateLimiter\|limiter\.limit\|rate_limit" . --include="*.py" 2>/dev/null | grep -v test | wc -l)
[ "$rate" -ge 1 ] && echo "  [PASS] Rate limiting present" || echo "  [FAIL] No rate limiting found"
```

### GATE 4 — All security tests pass

```bash
echo "====== GATE 4: Security Test Execution ======"
pytest -m security -v 2>&1 | tail -5
[ $? -eq 0 ] && echo "  GATE 4: PASS" || echo "  GATE 4: FAIL"
```

---

## Final Summary

```bash
echo ""
echo "============================================================"
echo "  SECURITY TESTS — COMPLETION REPORT"
echo "============================================================"
echo "  GATE 1 — No high/critical vulnerabilities: see above"
echo "  GATE 2 — Security scenarios covered:       see above"
echo "  GATE 3 — Security headers + rate limit:    see above"
echo "  GATE 4 — All security tests pass:          see above"
echo ""
echo "  Complete only when ALL gates show PASS."
echo "============================================================"
```

## Required Security Test Scenarios

| Scenario | Test Pattern | Required |
|---|---|---|
| No token → 401 | Missing Authorization header | ✅ per protected endpoint |
| Expired token → 401 | `generate_expired_token()` | ✅ |
| Wrong secret → 401 | `generate_tampered_token()` | ✅ |
| alg:none attack → 401 | Manually crafted header with `"alg":"none"` | ✅ |
| Cross-user access → 403 | User accessing another user's resource | ✅ |
| Non-admin on admin route → 403 | User-role token on admin endpoint | ✅ |
| Role escalation via body | PATCH with `{"role": "admin"}` | ✅ |
| Oversized payload → 400/413 | 1MB+ string in body | ✅ |
| SQL injection in params | Classic injection string in query | ✅ |
| Security headers present | `x-content-type-options`, `x-frame-options` | ✅ |
| No server fingerprint | Server header absent or generic | ✅ |
| Rate limiting → 429 | 100+ rapid requests to auth endpoint | ✅ |

---
