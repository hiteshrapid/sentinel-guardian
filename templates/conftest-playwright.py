"""
Playwright E2E test fixtures.
Template by Sentinel.

Built by Hitesh Goyal & Sentinel
"""

import pytest


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    return {
        **browser_context_args,
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
    if request.node.rep_call and request.node.rep_call.failed:
        test_name = request.node.name.replace("/", "_")
        page.screenshot(path=f"artifacts/screenshots/{test_name}.png")


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    import pytest
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)
