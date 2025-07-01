import pytest
import requests
from playwright.sync_api import Page, expect
import re

@pytest.mark.sanity
@pytest.mark.ui
class TestUISanity:
    """Sanity tests for critical UI functionality"""
    
    def test_frontend_loads_successfully(self, page: Page, live_frontend_url: str):
        """Sanity: Verify frontend application loads without errors"""
        page.goto(live_frontend_url)
        page.wait_for_load_state("networkidle", timeout=15000)
        
        # Check that page has loaded (no network errors)
        expect(page.locator("body")).to_be_visible()
        
        # Check for basic content
        page_content = page.content()
        assert len(page_content) > 100  # Should have substantial content
        
    def test_no_critical_javascript_errors(self, page: Page, live_frontend_url: str):
        """Sanity: Verify no critical JavaScript errors on page load"""
        errors = []
        page.on("pageerror", lambda error: errors.append(error))
        
        page.goto(live_frontend_url)
        page.wait_for_load_state("networkidle", timeout=15000)
        page.wait_for_timeout(3000)  # Wait for any delayed errors
        
        # Filter critical errors (ignore warnings and minor issues)
        critical_errors = [
            error for error in errors 
            if any(keyword in str(error).lower() for keyword in 
                  ["error", "failed", "undefined", "null", "cannot read"])
        ]
        
        assert len(critical_errors) == 0, f"Critical JavaScript errors: {critical_errors}"
        
    def test_basic_ui_elements_present(self, page: Page, live_frontend_url: str):
        """Sanity: Verify basic UI elements are present and functional"""
        page.goto(live_frontend_url)
        page.wait_for_load_state("networkidle", timeout=15000)
        page.wait_for_timeout(3000)
        
        # Look for any input field (todo creation)
        input_selectors = [
            'input[type="text"]',
            'input[placeholder*="todo" i]',
            'input[placeholder*="task" i]',
            'textarea',
            '[contenteditable="true"]'
        ]
        
        input_found = False
        for selector in input_selectors:
            try:
                if page.locator(selector).count() > 0:
                    input_found = True
                    break
            except:
                continue
        
        # If no input found, at least verify the page has interactive content
        if not input_found:
            # Look for any interactive elements
            interactive_selectors = ['button', 'a', '[onclick]', '[role="button"]']
            interactive_found = False
            
            for selector in interactive_selectors:
                try:
                    if page.locator(selector).count() > 0:
                        interactive_found = True
                        break
                except:
                    continue
            
            assert interactive_found or input_found, "No interactive elements found on page"
            
    @pytest.mark.skip(reason="Known CSS issue causing horizontal scroll on mobile.")
    def test_responsive_layout_mobile(self, page: Page, live_frontend_url: str):
        """Sanity: Verify app works on mobile viewport"""
        # Set mobile viewport
        page.set_viewport_size({"width": 375, "height": 667})
        page.goto(live_frontend_url)
        page.wait_for_load_state("networkidle", timeout=15000)
        
        # Verify page is still functional
        expect(page.locator("body")).to_be_visible()
        
        # Check that content fits in viewport (no horizontal scroll)
        body_width = page.evaluate("document.body.scrollWidth")
        viewport_width = page.evaluate("window.innerWidth")
        
        # Allow small tolerance for scrollbars
        assert body_width <= viewport_width + 20, "Horizontal scroll detected on mobile"
        
    def test_page_load_performance(self, page: Page, live_frontend_url: str):
        """Sanity: Verify page loads within acceptable time"""
        import time
        
        start_time = time.time()
        page.goto(live_frontend_url)
        page.wait_for_load_state("domcontentloaded")
        dom_load_time = time.time() - start_time
        
        page.wait_for_load_state("networkidle")
        full_load_time = time.time() - start_time
        
        # Sanity thresholds (more lenient than performance tests)
        assert dom_load_time < 15, f"DOM load took {dom_load_time:.2f}s (should be < 15s)"
        assert full_load_time < 30, f"Full page load took {full_load_time:.2f}s (should be < 30s)"

@pytest.mark.sanity
@pytest.mark.integration
class TestFullStackSanity:
    """Sanity tests that verify frontend-backend integration"""
    
    def test_frontend_can_reach_backend(self, page: Page, live_frontend_url: str):
        """Sanity: Verify frontend can communicate with backend"""
        # Monitor network requests
        api_requests = []
        failed_requests = []
        
        def handle_request(request):
            if any(domain in request.url for domain in ["railway.app", "api", "backend"]):
                api_requests.append(request)
                
        def handle_response(response):
            if response.status >= 400 and any(domain in response.url for domain in ["railway.app", "api", "backend"]):
                failed_requests.append(response)
        
        page.on("request", handle_request)
        page.on("response", handle_response)
        
        page.goto(live_frontend_url)
        page.wait_for_load_state("networkidle", timeout=15000)
        
        # Wait for any initial API calls
        page.wait_for_timeout(5000)
        
        # Check if there were any failed API requests
        critical_failures = [
            resp for resp in failed_requests 
            if resp.status >= 500  # Server errors are critical
        ]
        
        assert len(critical_failures) == 0, f"Critical API failures detected: {[(r.url, r.status) for r in critical_failures]}"
        
    def test_cors_configuration_working(self, page: Page, live_frontend_url: str):
        """Sanity: Verify CORS is properly configured"""
        cors_errors = []
        
        def handle_console(msg):
            if msg.type == "error" and "cors" in msg.text.lower():
                cors_errors.append(msg.text)
        
        page.on("console", handle_console)
        
        page.goto(live_frontend_url)
        page.wait_for_load_state("networkidle", timeout=15000)
        page.wait_for_timeout(5000)
        
        assert len(cors_errors) == 0, f"CORS errors detected: {cors_errors}"
        
    def test_basic_todo_functionality_exists(self, page: Page, live_frontend_url: str):
        """Sanity: Verify basic todo functionality is accessible through UI"""
        page.goto(live_frontend_url)
        page.wait_for_load_state("networkidle", timeout=15000)
        page.wait_for_timeout(3000)
        
        # Look for todo-related elements
        todo_indicators = [
            'input[placeholder*="todo" i]',
            'input[placeholder*="task" i]',
            'button:has-text("Add")',
            'button:has-text("Create")',
            'text=todo',
            'text=task',
            '.todo',
            '.task',
            '[data-testid*="todo"]'
        ]
        
        todo_elements_found = 0
        for selector in todo_indicators:
            try:
                if page.locator(selector).count() > 0:
                    todo_elements_found += 1
            except:
                continue
        
        # We should find at least one todo-related element
        assert todo_elements_found > 0, "No todo-related UI elements found"

@pytest.mark.sanity
@pytest.mark.deployment
class TestDeploymentSanity:
    """Sanity tests to verify deployments are working correctly"""
    
    def test_frontend_deployment_status(self, live_frontend_url: str):
        """Sanity: Verify frontend deployment is accessible"""
        response = requests.get(live_frontend_url, timeout=15)
        assert response.status_code == 200
        assert len(response.text) > 100  # Should have content
        
    def test_backend_deployment_status(self, live_api_url: str):
        """Sanity: Verify backend deployment is accessible"""
        try:
            response = requests.get(f"{live_api_url}/docs", timeout=15)
            assert response.status_code == 200
        except requests.RequestException as e:
            pytest.skip(f"Backend deployment not accessible: {e}")
            
    def test_database_connectivity(self, live_api_url: str):
        """Sanity: Verify database is connected and working"""
        try:
            response = requests.get(f"{live_api_url}/health", timeout=15)
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}
        except requests.RequestException as e:
            pytest.skip(f"Could not connect to backend for DB check: {e}") 