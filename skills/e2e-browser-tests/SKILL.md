---
name: e2e-browser-tests
description: >
  Implement Playwright browser end-to-end tests for critical user flows in web applications.
  Use this skill when the user wants to test login flows, form submissions, navigation,
  multi-page wizards, or any UI interaction in a real browser against a deployed service.
  Trigger when the user mentions "browser E2E", "Playwright tests", "UI E2E",
  "browser automation tests", "test the login flow", "test the signup page",
  "end-to-end browser tests", "visual regression", or "Page Object Model tests".
  This skill requires a frontend (React, Next.js, Vue, Angular, or server-rendered HTML).
  For API-only services without a frontend, use the e2e-api-tests skill instead.
---

# Browser End-to-End Tests Skill

## Stack Adaptation

Before writing any tests, detect the project's stack and load the matching context:

| Signal | Context File |
|--------|-------------|
| `from fastapi` + `beanie`/`motor` | `contexts/fastapi-beanie.md` |
| `from fastapi` + `sqlalchemy` | `contexts/fastapi-sqlalchemy.md` |
| `from flask` | `contexts/flask-sqlalchemy.md` |
| `from django` | `contexts/django-orm.md` |
| `package.json` + `next` + `prisma` | `contexts/nextjs-prisma.md` |

Read the context file for auth patterns and URL conventions specific to this stack.

---

You are an expert frontend QA engineer. Your mission: implement Playwright browser tests that
verify critical user flows work correctly in a real browser against a deployed service.

**Browser E2E tests answer: "Does the UI actually work for real users?"**

They are NOT:
- **Unit tests** — those test components in isolation with jsdom/testing-library
- **API E2E tests** — those test multi-step API workflows with httpx
- **Smoke tests** — those check if the service is alive

Browser E2E tests drive a real browser through complete user journeys.

---

## Phase 1 — Identify Critical UI Flows

Examine the frontend to identify user-facing flows:

```bash
# Find page/route definitions
# Next.js App Router
find app/ -name "page.tsx" -o -name "page.jsx" 2>/dev/null | head -20

# Next.js Pages Router
find pages/ -name "*.tsx" -o -name "*.jsx" 2>/dev/null | grep -v _app | grep -v _document | head -20

# React Router
grep -r "<Route\|createBrowserRouter" src/ --include="*.tsx" --include="*.jsx" -l 2>/dev/null | head -10

# Vue Router
grep -r "path:.*component:" src/router/ --include="*.ts" --include="*.js" 2>/dev/null | head -10

# Server-rendered (Django/Flask templates)
find . -name "*.html" -path "*/templates/*" 2>/dev/null | head -20
```

Common critical flows to test:

| Flow | Priority | Steps |
|---|---|---|
| Authentication | P0 | Login -> Dashboard, Logout, Failed login |
| Registration | P0 | Signup -> Email verify -> First login |
| Core CRUD | P0 | Create resource -> View -> Edit -> Delete |
| Navigation | P1 | Menu links, breadcrumbs, back button |
| Search/Filter | P1 | Enter query -> Results -> Clear -> Reset |
| Forms | P1 | Fill -> Validate -> Submit -> Confirm |
| Error states | P1 | 404 page, network error, empty states |
| Responsive | P2 | Mobile menu, tablet layout, desktop |

---

## Phase 2 — Install Playwright

### Python (pytest-playwright)
```bash
pip install playwright pytest-playwright
playwright install chromium
```

### Node.js (@playwright/test)
```bash
npm install --save-dev @playwright/test
npx playwright install chromium
```

---

## Phase 3 — Configure Playwright

### Python Configuration

```python
# tests/e2e_browser/conftest.py
import os
import pytest

BASE_URL = os.environ.get("E2E_BASE_URL", "http://localhost:3000")


def pytest_configure(config):
    config.addinivalue_line("markers", "e2e_browser: Playwright browser E2E tests")


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    return {
        **browser_context_args,
        "base_url": BASE_URL,
        "viewport": {"width": 1280, "height": 720},
        "record_video_dir": "artifacts/videos/",
    }


@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args):
    return {
        **browser_type_launch_args,
        "headless": True,
    }


@pytest.fixture(autouse=True)
def _screenshot_on_failure(request, page):
    """Auto-capture screenshot on test failure."""
    yield
    if hasattr(request.node, "rep_call") and request.node.rep_call.failed:
        test_name = request.node.name.replace("/", "_")
        page.screenshot(path=f"artifacts/screenshots/{test_name}.png")


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)
```

### Node.js Configuration

```typescript
// playwright.config.ts
import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e_browser",
  timeout: 30_000,
  retries: 1,
  use: {
    baseURL: process.env.E2E_BASE_URL || "http://localhost:3000",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    trace: "retain-on-failure",
  },
  projects: [
    { name: "chromium", use: { browserName: "chromium" } },
  ],
  outputDir: "artifacts/",
});
```

### pytest config

```toml
# pyproject.toml
[tool.pytest.ini_options]
markers = [
    # ... existing markers ...
    "e2e_browser: Playwright browser E2E tests against live deployed service",
]
```

**Makefile:**
```makefile
test-e2e-browser:
	pytest tests/e2e_browser/ -v --timeout=120

test-e2e-browser-headed:
	pytest tests/e2e_browser/ -v --headed --slowmo=500

test-e2e-browser-staging:
	E2E_BASE_URL=$(STAGING_URL) pytest tests/e2e_browser/ -v --timeout=120
```

---

## Phase 4 — File Structure

```
tests/
└── e2e_browser/
    ├── conftest.py              <- shared fixtures, screenshot-on-failure
    ├── pages/                   <- Page Object Model classes
    │   ├── __init__.py
    │   ├── login_page.py
    │   ├── dashboard_page.py
    │   ├── resource_page.py
    │   └── base_page.py         <- shared navigation, wait helpers
    ├── test_auth_flow.py        <- one file per user flow
    ├── test_resource_crud.py
    ├── test_navigation.py
    ├── test_forms.py
    └── test_error_states.py
artifacts/
├── screenshots/                 <- auto-captured on failure
└── videos/                      <- recorded on failure
```

**Naming convention:**
- Page objects: `{page_name}_page.py` with class `{PageName}Page`
- Test files: `test_{flow_name}.py` — named after the user flow
- Test methods: `test_{action}_{expected_result}`

---

## Phase 5 — Write Page Object Model Classes

### Base Page (shared helpers)

```python
# tests/e2e_browser/pages/base_page.py
from playwright.sync_api import Page, expect


class BasePage:
    """Shared helpers for all page objects."""

    def __init__(self, page: Page):
        self.page = page

    def navigate_to(self, path: str):
        self.page.goto(path)

    def get_by_testid(self, testid: str):
        return self.page.locator(f"[data-testid='{testid}']")

    def wait_for_navigation(self, url_pattern: str):
        self.page.wait_for_url(url_pattern)

    def screenshot(self, name: str):
        self.page.screenshot(path=f"artifacts/screenshots/{name}.png")

    def assert_toast(self, message: str):
        """Verify a toast/notification appears with expected text."""
        toast = self.page.locator("[role='alert'], .toast, .notification")
        expect(toast).to_contain_text(message, timeout=5000)
```

### Login Page

```python
# tests/e2e_browser/pages/login_page.py
from playwright.sync_api import Page, expect
from .base_page import BasePage


class LoginPage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)
        self.email_input = self.get_by_testid("email-input")
        self.password_input = self.get_by_testid("password-input")
        self.submit_button = self.get_by_testid("login-submit")
        self.error_message = self.get_by_testid("login-error")

    def goto(self):
        self.navigate_to("/login")
        return self

    def fill_credentials(self, email: str, password: str):
        self.email_input.fill(email)
        self.password_input.fill(password)
        return self

    def submit(self):
        self.submit_button.click()
        return self

    def login(self, email: str, password: str):
        """Complete login flow."""
        self.goto()
        self.fill_credentials(email, password)
        self.submit()
        return self

    def assert_login_error(self, message: str):
        expect(self.error_message).to_be_visible()
        expect(self.error_message).to_contain_text(message)

    def assert_redirected_to_dashboard(self):
        self.wait_for_navigation("**/dashboard**")
```

### Dashboard Page

```python
# tests/e2e_browser/pages/dashboard_page.py
from playwright.sync_api import Page, expect
from .base_page import BasePage


class DashboardPage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)
        self.welcome_text = self.get_by_testid("welcome-message")
        self.nav_menu = self.get_by_testid("main-nav")
        self.logout_button = self.get_by_testid("logout-button")
        self.create_button = self.get_by_testid("create-new")

    def goto(self):
        self.navigate_to("/dashboard")
        return self

    def assert_logged_in(self, username: str = None):
        expect(self.welcome_text).to_be_visible()
        if username:
            expect(self.welcome_text).to_contain_text(username)

    def logout(self):
        self.logout_button.click()
        self.wait_for_navigation("**/login**")

    def click_create_new(self):
        self.create_button.click()
```

### Resource Page (generic CRUD page)

```python
# tests/e2e_browser/pages/resource_page.py
from playwright.sync_api import Page, expect
from .base_page import BasePage


class ResourcePage(BasePage):
    """Generic page object for CRUD resources (campaigns, projects, etc.)"""

    def __init__(self, page: Page, resource_name: str):
        super().__init__(page)
        self.resource_name = resource_name
        self.list_items = self.page.locator(f"[data-testid='{resource_name}-list-item']")
        self.create_button = self.get_by_testid(f"create-{resource_name}")
        self.name_input = self.get_by_testid(f"{resource_name}-name")
        self.save_button = self.get_by_testid("save-button")
        self.delete_button = self.get_by_testid("delete-button")
        self.confirm_delete = self.get_by_testid("confirm-delete")
        self.empty_state = self.get_by_testid("empty-state")

    def goto_list(self):
        self.navigate_to(f"/{self.resource_name}")
        return self

    def click_create(self):
        self.create_button.click()
        return self

    def fill_name(self, name: str):
        self.name_input.fill(name)
        return self

    def save(self):
        self.save_button.click()
        return self

    def delete_current(self):
        self.delete_button.click()
        self.confirm_delete.click()
        return self

    def assert_item_in_list(self, name: str):
        expect(self.page.locator(f"text={name}")).to_be_visible()

    def assert_item_not_in_list(self, name: str):
        expect(self.page.locator(f"text={name}")).not_to_be_visible()

    def assert_empty_state(self):
        expect(self.empty_state).to_be_visible()

    def count_items(self) -> int:
        return self.list_items.count()
```

---

## Phase 6 — Write Browser E2E Tests

### Pattern A — Authentication Flow

```python
# tests/e2e_browser/test_auth_flow.py
import pytest
from playwright.sync_api import Page, expect
from pages.login_page import LoginPage
from pages.dashboard_page import DashboardPage

pytestmark = [pytest.mark.e2e_browser]


class TestLoginFlow:
    def test_successful_login_redirects_to_dashboard(self, page: Page):
        login = LoginPage(page).goto()
        login.fill_credentials("user@test.com", "password123")
        login.submit()
        login.assert_redirected_to_dashboard()
        login.screenshot("login-success")

    def test_invalid_password_shows_error(self, page: Page):
        login = LoginPage(page).goto()
        login.fill_credentials("user@test.com", "wrongpassword")
        login.submit()
        login.assert_login_error("Invalid credentials")
        login.screenshot("login-error")

    def test_empty_form_shows_validation(self, page: Page):
        login = LoginPage(page).goto()
        login.submit()
        expect(login.email_input).to_have_attribute("required", "")

    def test_login_then_logout(self, page: Page):
        login = LoginPage(page)
        login.login("user@test.com", "password123")
        dashboard = DashboardPage(page)
        dashboard.assert_logged_in()
        dashboard.logout()
        expect(page).to_have_url("**/login**")


class TestProtectedRoutes:
    def test_dashboard_redirects_to_login_when_unauthenticated(self, page: Page):
        page.goto("/dashboard")
        expect(page).to_have_url("**/login**")

    def test_settings_redirects_to_login_when_unauthenticated(self, page: Page):
        page.goto("/settings")
        expect(page).to_have_url("**/login**")
```

### Pattern B — Resource CRUD via UI

```python
# tests/e2e_browser/test_resource_crud.py
import pytest
from playwright.sync_api import Page, expect
from pages.login_page import LoginPage
from pages.resource_page import ResourcePage

pytestmark = [pytest.mark.e2e_browser]


class TestResourceCRUD:
    """Full CRUD lifecycle through the UI."""

    @pytest.fixture(autouse=True)
    def _login(self, page: Page):
        LoginPage(page).login("user@test.com", "password123")

    def test_create_resource(self, page: Page):
        resource = ResourcePage(page, "project")
        resource.goto_list()
        resource.click_create()
        resource.fill_name("E2E Test Project")
        resource.save()
        resource.assert_toast("Created successfully")
        resource.screenshot("resource-created")

    def test_created_resource_appears_in_list(self, page: Page):
        resource = ResourcePage(page, "project")
        resource.goto_list()
        resource.assert_item_in_list("E2E Test Project")

    def test_edit_resource(self, page: Page):
        resource = ResourcePage(page, "project")
        resource.goto_list()
        page.locator("text=E2E Test Project").click()
        resource.fill_name("E2E Updated Project")
        resource.save()
        resource.assert_toast("Updated successfully")

    def test_delete_resource(self, page: Page):
        resource = ResourcePage(page, "project")
        resource.goto_list()
        page.locator("text=E2E Updated Project").click()
        resource.delete_current()
        resource.assert_toast("Deleted")
        resource.assert_item_not_in_list("E2E Updated Project")
        resource.screenshot("resource-deleted")
```

### Pattern C — Form Validation

```python
# tests/e2e_browser/test_forms.py
import pytest
from playwright.sync_api import Page, expect

pytestmark = [pytest.mark.e2e_browser]


class TestFormValidation:
    @pytest.fixture(autouse=True)
    def _login(self, page: Page):
        from pages.login_page import LoginPage
        LoginPage(page).login("user@test.com", "password123")

    def test_required_fields_show_errors(self, page: Page):
        page.goto("/projects/new")
        page.locator("[data-testid='save-button']").click()
        error = page.locator("[data-testid='name-error'], .field-error")
        expect(error).to_be_visible()

    def test_invalid_email_format_rejected(self, page: Page):
        page.goto("/settings/profile")
        page.locator("[data-testid='email-input']").fill("not-an-email")
        page.locator("[data-testid='save-button']").click()
        error = page.locator("[data-testid='email-error']")
        expect(error).to_be_visible()

    def test_max_length_enforced(self, page: Page):
        page.goto("/projects/new")
        long_name = "x" * 500
        page.locator("[data-testid='project-name']").fill(long_name)
        page.locator("[data-testid='save-button']").click()
        error = page.locator("[data-testid='name-error']")
        expect(error).to_be_visible()
```

### Pattern D — Navigation and Error States

```python
# tests/e2e_browser/test_navigation.py
import pytest
from playwright.sync_api import Page, expect

pytestmark = [pytest.mark.e2e_browser]


class TestNavigation:
    @pytest.fixture(autouse=True)
    def _login(self, page: Page):
        from pages.login_page import LoginPage
        LoginPage(page).login("user@test.com", "password123")

    def test_main_nav_links_work(self, page: Page):
        page.goto("/dashboard")
        for link_text, expected_url in [
            ("Projects", "/projects"),
            ("Settings", "/settings"),
            ("Dashboard", "/dashboard"),
        ]:
            page.locator(f"nav >> text={link_text}").click()
            expect(page).to_have_url(f"**{expected_url}**")

    def test_404_page_for_nonexistent_route(self, page: Page):
        page.goto("/this-page-does-not-exist-xyz")
        expect(page.locator("text=404")).to_be_visible()
        expect(page.locator("text=Traceback")).not_to_be_visible()

    def test_browser_back_button_works(self, page: Page):
        page.goto("/dashboard")
        page.goto("/settings")
        page.go_back()
        expect(page).to_have_url("**/dashboard**")
```

### Pattern E — Responsive Layout

```python
# tests/e2e_browser/test_responsive.py
import pytest
from playwright.sync_api import Page, expect

pytestmark = [pytest.mark.e2e_browser]

MOBILE = {"width": 375, "height": 812}
TABLET = {"width": 768, "height": 1024}
DESKTOP = {"width": 1280, "height": 720}


class TestResponsiveLayout:
    @pytest.fixture(autouse=True)
    def _login(self, page: Page):
        from pages.login_page import LoginPage
        LoginPage(page).login("user@test.com", "password123")

    def test_mobile_hamburger_menu(self, page: Page):
        page.set_viewport_size(MOBILE)
        page.goto("/dashboard")
        hamburger = page.locator("[data-testid='mobile-menu-toggle']")
        expect(hamburger).to_be_visible()
        hamburger.click()
        expect(page.locator("[data-testid='mobile-nav']")).to_be_visible()
        page.screenshot(path="artifacts/screenshots/mobile-menu.png")

    def test_desktop_sidebar_visible(self, page: Page):
        page.set_viewport_size(DESKTOP)
        page.goto("/dashboard")
        sidebar = page.locator("[data-testid='sidebar']")
        expect(sidebar).to_be_visible()
```

---

## Phase 7 — Selector Strategy

### Priority Order for Selectors

| Priority | Selector | Example | When to Use |
|---|---|---|---|
| 1 (best) | data-testid | `[data-testid="login-submit"]` | Always preferred |
| 2 | Role | `getByRole("button", {name: "Submit"})` | Accessible elements |
| 3 | Text | `text=Submit` | Labels, headings |
| 4 (avoid) | CSS class | `.btn-primary` | Only as last resort |

### Rules
- **NEVER** use CSS classes as primary selectors — they change with styling
- **ALWAYS** prefer `data-testid` — stable, explicit, test-only
- If `data-testid` is missing, add it to the source before writing the test
- Use `getByRole` for accessible elements (buttons, links, inputs)
- Use `text=` for visible text content (headings, labels)

---

## Phase 8 — Anti-Flakiness Patterns

### Wait for conditions, not time
```python
# BAD - arbitrary sleep
import time
time.sleep(3)
page.click("button")

# GOOD - wait for specific condition
page.wait_for_selector("[data-testid='loaded']")
page.click("button")

# GOOD - wait for network idle
page.wait_for_load_state("networkidle")

# GOOD - wait for specific response
with page.expect_response("**/api/data") as response_info:
    page.click("[data-testid='load-data']")
response = response_info.value
```

### Retry flaky interactions
```python
# For elements that appear after animation
expect(element).to_be_visible(timeout=5000)

# For dynamic content
page.wait_for_selector("text=Loaded", state="visible", timeout=10000)
```

### Isolate tests
```python
# Each test starts fresh — no dependency on previous test state
@pytest.fixture(autouse=True)
def _clean_state(page: Page):
    page.goto("/dashboard")
    yield
```

---

## Phase 9 — CI Integration

### In deploy.yml (after API E2E)

```yaml
e2e-browser:
  name: Browser E2E Tests
  runs-on: ubuntu-latest
  needs: e2e-api  # Run after API E2E passes
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with: { python-version: "3.12" }
    - run: pip install playwright pytest-playwright
    - run: playwright install --with-deps chromium
    - name: Run Browser E2E
      run: pytest tests/e2e_browser/ -v --timeout=120
      timeout-minutes: 5
      env:
        E2E_BASE_URL: ${{ needs.deploy.outputs.deploy_url }}
    - name: Upload artifacts
      if: always()
      uses: actions/upload-artifact@v4
      with:
        name: e2e-browser-artifacts
        path: |
          artifacts/screenshots/
          artifacts/videos/
```

### In regression.yml (nightly)

```yaml
regression-e2e-browser:
  name: Browser E2E (Nightly)
  runs-on: ubuntu-latest
  needs: regression-e2e-api
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with: { python-version: "3.12" }
    - run: pip install playwright pytest-playwright
    - run: playwright install --with-deps chromium
    - run: pytest tests/e2e_browser/ -v --timeout=120
      env:
        E2E_BASE_URL: ${{ vars.DEV_URL }}
    - uses: actions/upload-artifact@v4
      if: always()
      with:
        name: e2e-browser-artifacts
        path: artifacts/
```

---

## Phase 10 — Verification Gates

### GATE 1 — Page objects exist

```bash
echo "====== GATE 1: Page Object Model ======"
pages=$(find tests/e2e_browser/pages -name "*_page.py" 2>/dev/null | wc -l)
[ "$pages" -ge 2 ] \
  && echo "  PASS — $pages page objects" \
  || echo "  FAIL — Need at least login_page.py + one resource page"
```

### GATE 2 — Tests use data-testid selectors

```bash
echo "====== GATE 2: Selector Strategy ======"
testid=$(grep -r "data-testid\|get_by_testid\|getByTestId" tests/e2e_browser/ --include="*.py" --include="*.ts" 2>/dev/null | wc -l)
css_class=$(grep -r "\.btn-\|\.card-\|\.nav-" tests/e2e_browser/ --include="*.py" --include="*.ts" 2>/dev/null | wc -l)
[ "$testid" -ge 3 ] && echo "  PASS — $testid data-testid usages" || echo "  FAIL — Use data-testid selectors"
[ "$css_class" -le 2 ] && echo "  PASS — minimal CSS class selectors" || echo "  WARN — $css_class CSS class selectors (prefer data-testid)"
```

### GATE 3 — Screenshots captured

```bash
echo "====== GATE 3: Screenshots ======"
screenshots=$(grep -r "screenshot" tests/e2e_browser/ --include="*.py" 2>/dev/null | wc -l)
[ "$screenshots" -ge 2 ] \
  && echo "  PASS — $screenshots screenshot calls" \
  || echo "  FAIL — Add screenshots at critical steps"
```

### GATE 4 — No sleep-based waits

```bash
echo "====== GATE 4: No Flaky Waits ======"
sleeps=$(grep -r "time.sleep\|page.wait_for_timeout" tests/e2e_browser/ --include="*.py" 2>/dev/null | wc -l)
[ "$sleeps" -eq 0 ] \
  && echo "  PASS — no sleep-based waits" \
  || echo "  FAIL — $sleeps sleep calls (use wait_for_selector or expect instead)"
```

### GATE 5 — All browser E2E tests pass

```bash
echo "====== GATE 5: Test Execution ======"
E2E_BASE_URL=${E2E_BASE_URL:-http://localhost:3000} \
  pytest tests/e2e_browser/ -v --timeout=120 2>&1 | tail -5
[ $? -eq 0 ] && echo "  GATE 5: PASS" || echo "  GATE 5: FAIL"
```

### GATE 6 — CI workflow has browser E2E job

```bash
echo "====== GATE 6: CI Integration ======"
grep -q "e2e.browser\|e2e_browser\|playwright" .github/workflows/deploy.yml 2>/dev/null \
  && echo "  PASS — Browser E2E in deploy.yml" \
  || echo "  FAIL — Add browser E2E job to deploy.yml"
```

---

## Critical Rules

1. **Page Object Model is mandatory** — no raw selectors in test files
2. **data-testid selectors only** — never rely on CSS classes or DOM structure
3. **Screenshot at critical steps** — login success, resource created, error states
4. **No time.sleep()** — use wait_for_selector, expect, wait_for_response
5. **Each test is independent** — no shared state between tests
6. **Video on failure only** — saves CI time and disk space
7. **Run locally 3x before committing** — catch flakiness early
8. **Artifacts uploaded in CI** — screenshots + videos available for debugging
9. **Headless in CI, headed locally** — use --headed flag for local debugging
10. **Add data-testid to source if missing** — test infrastructure is part of the codebase

---

## Where This Fits in the Testing Pyramid

```
On every PR (ci.yml):
  Unit tests        -> fast, < 3 min
  Integration tests -> real DB, 3-8 min
  Contract tests    -> schema diff, < 2 min
  Security audit    -> pip-audit, < 2 min

On merge to main (deploy.yml):
  Deploy to staging
  Smoke tests       -> health checks, < 60 sec
  API E2E tests     -> business workflows, < 2 min
  Browser E2E       -> Playwright UI flows, < 5 min    <- THIS SKILL

Nightly (regression.yml):
  Full suite + API E2E + Browser E2E + Slack alert
```

## What comes next

- **Visual regression** — screenshot comparison with Percy or Playwright snapshots
- **Accessibility testing** — axe-core integration via @axe-core/playwright
