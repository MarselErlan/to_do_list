import pytest
from playwright.sync_api import Playwright, Browser, BrowserContext, Page

# Configuration for Playwright tests
BASE_URL = "https://marsel-to-do-list.vercel.app"

@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """Configure browser context for all tests"""
    return {
        **browser_context_args,
        "viewport": {"width": 1280, "height": 720},
        "ignore_https_errors": True,
    }

@pytest.fixture(scope="session") 
def base_url():
    """Base URL for the todo app"""
    return BASE_URL

@pytest.fixture
def context(browser):
    """Create a new browser context for each test"""
    context = browser.new_context(
        viewport={"width": 1280, "height": 720},
        ignore_https_errors=True
    )
    yield context
    context.close()

@pytest.fixture
def page(context):
    """Create a new page for each test"""
    page = context.new_page()
    yield page
    page.close() 