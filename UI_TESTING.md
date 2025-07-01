# UI Testing with Playwright

This document describes the UI testing setup for the Todo application using Playwright.

## Overview

The UI tests verify that the frontend application at [https://marsel-to-do-list.vercel.app/](https://marsel-to-do-list.vercel.app/) works correctly and integrates properly with the Railway backend API.

## Test Structure

```
tests/ui/
├── conftest.py              # Playwright configuration and fixtures
├── test_todo_ui.py          # Core UI functionality tests
└── test_api_integration.py  # Frontend-backend integration tests
```

## Test Categories

### 1. Core UI Tests (`test_todo_ui.py`)

- **Page Loading**: Verifies the application loads successfully
- **Todo Creation**: Tests adding new todo items through the UI
- **Todo List Display**: Checks that todos are displayed correctly
- **Todo Interactions**: Tests UI interactions (checkboxes, buttons)
- **Responsive Design**: Verifies the app works on different screen sizes
- **Performance**: Checks page load times and JavaScript errors

### 2. API Integration Tests (`test_api_integration.py`)

- **Frontend-Backend Connectivity**: Verifies API communication
- **CRUD Operations**: Tests complete todo lifecycle through UI
- **Error Handling**: Checks how UI handles API errors
- **Loading States**: Verifies loading indicators work properly
- **Data Persistence**: Tests that data survives page refreshes

## Running UI Tests

### Quick Start

```bash
# Run all UI tests
./run_ui_tests.sh

# Run with specific browser
./run_ui_tests.sh firefox

# Run specific test
./run_ui_tests.sh chromium tests/ui/test_todo_ui.py::TestTodoUI::test_page_loads_successfully
```

### Manual Commands

```bash
# Set up environment
export PYTHONPATH=.

# Run all UI tests with Chromium
./venv/bin/pytest tests/ui/ -v --browser=chromium

# Run with different browsers
./venv/bin/pytest tests/ui/ -v --browser=firefox
./venv/bin/pytest tests/ui/ -v --browser=webkit

# Generate HTML report
./venv/bin/pytest tests/ui/ -v --browser=chromium --html=reports/ui_test_report.html
```

## Test Configuration

### Browser Settings

- **Default Browser**: Chromium
- **Viewport**: 1280x720 (configurable)
- **Timeout**: 30 seconds per test
- **HTTPS Errors**: Ignored for testing

### Application URLs

- **Frontend**: https://marsel-to-do-list.vercel.app/
- **Backend**: Your Railway deployment URL

## Test Features

### Intelligent Element Detection

The tests use multiple selector strategies to find UI elements:

- Placeholder text matching
- Data test IDs
- CSS classes
- Button text content
- Element types

### Cross-Browser Support

Tests can run on:

- ✅ Chromium (default)
- ✅ Firefox
- ✅ WebKit (Safari)

### Responsive Testing

Automatically tests multiple viewport sizes:

- 📱 Mobile: 375x667
- 📱 Tablet: 768x1024
- 💻 Desktop: 1280x720

### Performance Monitoring

- Page load time measurement
- JavaScript error detection
- Network request monitoring

## Test Reports

After running tests, view the HTML report:

```bash
open reports/ui_test_report.html
```

The report includes:

- Test results and duration
- Screenshots on failures
- Browser and environment details
- Test logs and errors

## Debugging Tests

### Running in Headed Mode

```bash
./venv/bin/pytest tests/ui/ -v --browser=chromium --headed
```

### Adding Debug Breakpoints

```python
# In your test
page.pause()  # Opens Playwright Inspector
```

### Verbose Output

```bash
./venv/bin/pytest tests/ui/ -v -s --browser=chromium
```

## CI/CD Integration

### GitHub Actions Example

```yaml
- name: Install Playwright
  run: |
    pip install playwright pytest-playwright
    playwright install

- name: Run UI Tests
  run: |
    PYTHONPATH=. pytest tests/ui/ --browser=chromium --html=reports/ui_report.html
```

### Railway Integration

The tests automatically work with your Railway backend deployment since the CORS settings include Railway domains.

## Best Practices

### Test Writing

1. **Use data-testid attributes** in your frontend for reliable element selection
2. **Wait for network idle** before asserting UI state
3. **Test critical user journeys** end-to-end
4. **Include error scenarios** and edge cases

### Maintenance

1. **Update selectors** when UI changes
2. **Keep tests independent** - each test should work alone
3. **Use descriptive test names** that explain what's being tested
4. **Group related tests** in logical classes

### Performance

1. **Run tests in parallel** when possible
2. **Use headless mode** in CI/CD
3. **Cache browser installations** in CI
4. **Set appropriate timeouts** for slow operations

## Troubleshooting

### Common Issues

**"Element not found" errors:**

```bash
# Add wait time or use different selector
page.wait_for_selector("your-selector", timeout=10000)
```

**CORS errors:**

- Verify Railway backend CORS settings include frontend domain
- Check network tab in browser for failed requests

**Test timeouts:**

```bash
# Increase timeout in conftest.py or test
page.set_default_timeout(60000)  # 60 seconds
```

**Browser installation issues:**

```bash
# Reinstall browsers
./venv/bin/playwright install
```

## Contributing

When adding new UI tests:

1. Follow the existing test structure
2. Add appropriate markers (`@pytest.mark.ui`)
3. Include both positive and negative test cases
4. Update this documentation if needed
5. Ensure tests work across different browsers

## Dependencies

- `playwright` - Browser automation
- `pytest-playwright` - Pytest integration
- `pytest-html` - HTML test reports
- `pytest` - Test framework
