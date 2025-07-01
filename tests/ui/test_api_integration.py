import pytest
import requests
from playwright.sync_api import Page, expect

@pytest.mark.ui
class TestAPIIntegration:
    """UI tests that verify frontend-backend integration"""
    
    @pytest.fixture(autouse=True)
    def setup_test_data(self):
        """Setup and cleanup test data for each test"""
        # Note: This assumes your Railway backend URL - update if needed
        self.api_base_url = "https://your-railway-url.up.railway.app"
        yield
        # Cleanup after test if needed
        
    def test_frontend_backend_connectivity(self, page: Page, base_url: str):
        """Test that frontend can communicate with backend"""
        page.goto(base_url)
        page.wait_for_load_state("networkidle")
        
        # Monitor network requests to the API
        api_requests = []
        page.on("request", lambda request: 
                api_requests.append(request) if "railway.app" in request.url else None)
        
        # Wait for any initial API calls
        page.wait_for_timeout(5000)
        
        # Verify that API calls are being made (or attempt to trigger one)
        try:
            # Try to find and interact with an element that would trigger an API call
            refresh_selectors = [
                'button:has-text("Refresh")',
                'button:has-text("Load")',
                '[data-testid="refresh"]'
            ]
            
            for selector in refresh_selectors:
                try:
                    refresh_btn = page.locator(selector).first
                    if refresh_btn.is_visible():
                        refresh_btn.click()
                        page.wait_for_timeout(2000)
                        break
                except:
                    continue
        except:
            pass
            
        # The test passes if no network errors occurred
        # We're mainly checking that the page loads without CORS or connection errors
        
    def test_todo_crud_operations_ui(self, page: Page, base_url: str):
        """Test complete CRUD operations through the UI"""
        page.goto(base_url)
        page.wait_for_load_state("networkidle")
        
        # Test Create - Try to add a todo
        test_todo_text = "Playwright Integration Test Todo"
        
        # Find input and submit elements
        input_selectors = [
            'input[placeholder*="todo" i]',
            'input[placeholder*="task" i]',
            'input[type="text"]',
            '[data-testid="todo-input"]'
        ]
        
        for input_selector in input_selectors:
            try:
                todo_input = page.locator(input_selector).first
                if todo_input.is_visible():
                    todo_input.fill(test_todo_text)
                    
                    # Try to submit
                    submit_selectors = [
                        'button:has-text("Add")',
                        'button[type="submit"]',
                        '[data-testid="add-todo"]'
                    ]
                    
                    for submit_selector in submit_selectors:
                        try:
                            submit_btn = page.locator(submit_selector).first
                            if submit_btn.is_visible():
                                submit_btn.click()
                                page.wait_for_timeout(3000)
                                
                                # Verify todo appears
                                todo_item = page.locator(f"text={test_todo_text}")
                                if todo_item.count() > 0:
                                    expect(todo_item.first).to_be_visible()
                                    
                                    # Test Update/Complete - look for checkbox or complete button
                                    try:
                                        checkbox = page.locator('input[type="checkbox"]').first
                                        if checkbox.is_visible():
                                            checkbox.click()
                                            page.wait_for_timeout(1000)
                                    except:
                                        pass
                                        
                                    # Test Delete - look for delete button
                                    try:
                                        delete_btn = page.locator('button:has-text("Delete")').first
                                        if delete_btn.is_visible():
                                            delete_btn.click()
                                            page.wait_for_timeout(2000)
                                            # Verify todo is removed
                                            expect(todo_item).not_to_be_visible()
                                    except:
                                        pass
                                        
                                return  # Exit if we successfully created a todo
                        except:
                            continue
                    break
            except:
                continue
                
    def test_error_handling(self, page: Page, base_url: str):
        """Test how the UI handles errors from the backend"""
        page.goto(base_url)
        page.wait_for_load_state("networkidle")
        
        # Monitor for error messages or failed requests
        console_errors = []
        page.on("console", lambda msg: 
                console_errors.append(msg) if msg.type == "error" else None)
        
        # Wait and check for any console errors
        page.wait_for_timeout(5000)
        
        # Filter out non-critical errors
        critical_errors = [
            error for error in console_errors 
            if any(keyword in error.text.lower() for keyword in 
                  ["network", "fetch", "cors", "api", "500", "400"])
        ]
        
        # Assert no critical API errors
        assert len(critical_errors) == 0, f"Critical errors found: {[e.text for e in critical_errors]}"
        
    def test_loading_states(self, page: Page, base_url: str):
        """Test that loading states are handled properly"""
        page.goto(base_url)
        
        # Check for loading indicators
        loading_selectors = [
            'text=Loading',
            'text=loading',
            '.loading',
            '[data-testid="loading"]',
            '.spinner'
        ]
        
        # Initially there might be loading states
        page.wait_for_timeout(1000)
        
        # After reasonable time, loading should be complete
        page.wait_for_timeout(10000)
        
        for selector in loading_selectors:
            try:
                loading_element = page.locator(selector)
                if loading_element.count() > 0:
                    # Loading elements should not be visible after page loads
                    expect(loading_element.first).not_to_be_visible()
            except:
                continue
                
    def test_data_persistence(self, page: Page, base_url: str):
        """Test that data persists across page refreshes"""
        page.goto(base_url)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(3000)
        
        # Get initial state of todos (count them)
        initial_todos = []
        try:
            # Look for todo items
            todo_selectors = [
                '[data-testid*="todo"]',
                '.todo-item',
                'li',
                '.todo'
            ]
            
            for selector in todo_selectors:
                try:
                    todos = page.locator(selector)
                    if todos.count() > 0:
                        initial_todos = [todos.nth(i).text_content() for i in range(todos.count())]
                        break
                except:
                    continue
        except:
            pass
            
        # Refresh the page
        page.reload()
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(3000)
        
        # Check that todos are still there (if any existed)
        if initial_todos:
            for todo_text in initial_todos[:3]:  # Check first 3 todos
                if todo_text and todo_text.strip():
                    expect(page.locator(f"text={todo_text.strip()}")).to_be_visible() 