import pytest
from playwright.sync_api import Browser, BrowserContext, Page

@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """Configure browser context for sanity tests"""
    return {
        **browser_context_args,
        "viewport": {"width": 1280, "height": 720},
        "ignore_https_errors": True,
    }

@pytest.fixture
def context(browser):
    """Create a new browser context for each sanity test"""
    context = browser.new_context(
        viewport={"width": 1280, "height": 720},
        ignore_https_errors=True
    )
    yield context
    context.close()

@pytest.fixture
def page(context):
    """Create a new page for each sanity test"""
    page = context.new_page()
    yield page
    page.close() 