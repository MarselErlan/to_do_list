# Sanity Testing for Todo Application

This document explains the sanity testing implementation for the Todo application, which verifies that critical functionality works correctly after changes or deployments.

## What is Sanity Testing?

Sanity testing is a subset of regression testing that focuses on verifying that the most critical functionality of an application still works after:

- Code changes
- Bug fixes
- Minor enhancements
- Deployments
- Environment changes

It's a **quick verification** that ensures the core features are working correctly before running more comprehensive tests.

## Test Architecture

```
tests/sanity/
├── conftest.py              # Shared fixtures for API and general tests
├── ui_conftest.py           # Playwright-specific fixtures
├── test_api_sanity.py       # API sanity tests
└── test_ui_sanity.py        # UI and integration sanity tests
```

## Test Categories

### 1. API Sanity Tests (`test_api_sanity.py`)

#### Local API Tests

- ✅ **Health Check**: API responds correctly
- ✅ **Basic CRUD**: Create, read, update, delete todos
- ✅ **Complete Workflow**: End-to-end todo operations
- ✅ **Data Validation**: Proper response formats

#### Live API Tests

- 🌐 **Deployment Health**: Live API accessibility
- 🌐 **Endpoint Functionality**: Core endpoints work
- 🌐 **CORS Configuration**: Headers are correct

### 2. UI Sanity Tests (`test_ui_sanity.py`)

#### Basic UI Tests

- 🖥️ **Page Loading**: Frontend loads without errors
- 🖥️ **JavaScript Errors**: No critical JS errors
- 🖥️ **UI Elements**: Essential elements are present
- 🖥️ **Responsive Design**: Works on mobile devices
- 🖥️ **Performance**: Acceptable load times

#### Integration Tests

- 🔗 **Frontend-Backend**: Communication works
- 🔗 **CORS Configuration**: No CORS errors
- 🔗 **Todo Functionality**: UI shows todo features

#### Deployment Tests

- 🚀 **Frontend Status**: Vercel deployment accessible
- 🚀 **Backend Status**: Railway deployment accessible
- 🚀 **Database Connectivity**: Database connections work

## Running Sanity Tests

### Quick Start

```bash
# Run essential sanity checks (fastest)
./run_sanity_tests.sh quick

# Run local API tests only
./run_sanity_tests.sh local

# Run all sanity tests
./run_sanity_tests.sh all
```

### Test Modes

| Mode           | Description             | Tests Included                          | Duration     |
| -------------- | ----------------------- | --------------------------------------- | ------------ |
| `quick`        | Essential health checks | Health, loading, status                 | ~30 seconds  |
| `local`        | Local API tests only    | API functionality without live services | ~10 seconds  |
| `api`          | All API tests           | Local + live API tests                  | ~30 seconds  |
| `ui`           | UI tests only           | Frontend functionality                  | ~45 seconds  |
| `integration`  | Frontend-backend tests  | Cross-service communication             | ~60 seconds  |
| `deployment`   | Deployment status       | Service availability                    | ~20 seconds  |
| `all` / `full` | Complete sanity suite   | All tests                               | ~2-3 minutes |

### Command Examples

```bash
# Quick health check
./run_sanity_tests.sh quick

# Test with different browser
./run_sanity_tests.sh ui firefox

# Local development testing
./run_sanity_tests.sh local

# Pre-deployment verification
./run_sanity_tests.sh deployment

# Post-deployment verification
./run_sanity_tests.sh all
```

## Test Markers

Tests are organized using pytest markers:

```python
@pytest.mark.sanity          # All sanity tests
@pytest.mark.sanity          # Core sanity functionality
@pytest.mark.live            # Requires live deployments
@pytest.mark.ui              # Requires Playwright
@pytest.mark.integration     # Cross-service tests
@pytest.mark.deployment      # Deployment verification
```

### Running by Markers

```bash
# Run only local tests (no live services)
pytest tests/sanity/ -m "sanity and not live"

# Run only UI tests
pytest tests/sanity/ -m "sanity and ui"

# Run only deployment tests
pytest tests/sanity/ -m "sanity and deployment"
```

## Configuration

### Environment Variables

```bash
# Override live API URL
export LIVE_API_URL="https://your-railway-app.up.railway.app"

# Frontend URL (auto-configured)
# Uses: https://marsel-to-do-list.vercel.app
```

### Browser Configuration

- **Default**: Chromium
- **Supported**: Chromium, Firefox, WebKit
- **Headless**: Yes (default for CI)
- **Headed**: Use `--headed` flag for debugging

## When to Run Sanity Tests

### Development Workflow

1. **Before Commits**: `./run_sanity_tests.sh quick`
2. **After Major Changes**: `./run_sanity_tests.sh local`
3. **Before Deployment**: `./run_sanity_tests.sh deployment`
4. **After Deployment**: `./run_sanity_tests.sh all`

### CI/CD Pipeline

```yaml
# Example GitHub Actions
- name: Sanity Tests
  run: |
    ./run_sanity_tests.sh quick

- name: Full Sanity Check
  run: |
    ./run_sanity_tests.sh all
```

### Monitoring & Alerts

- **Schedule**: Run every 15-30 minutes in production
- **Alert on**: Any sanity test failure
- **Dashboard**: Monitor sanity test results

## Test Reports

Sanity tests generate HTML reports in the `reports/` directory:

```bash
reports/
├── sanity_quick_report.html      # Quick test results
├── sanity_local_report.html      # Local API test results
├── sanity_full_report.html       # Complete sanity results
└── sanity_ui_report.html         # UI test results
```

### Viewing Reports

```bash
# Open latest report
open reports/sanity_quick_report.html

# Or view in browser
python -m http.server 8000
# Visit: http://localhost:8000/reports/
```

## Interpreting Results

### ✅ All Tests Pass

```
🚀 System Status: HEALTHY ✅
```

- Core functionality working
- Safe to proceed with changes
- System is stable

### ❌ Some Tests Fail

```
🚨 System Status: NEEDS ATTENTION ❌
```

- Critical functionality broken
- Investigation required
- Hold deployments until fixed

### Common Failure Scenarios

#### Frontend Issues

- Page won't load → Check Vercel deployment
- JavaScript errors → Check console logs
- CORS errors → Verify backend CORS settings

#### Backend Issues

- API not responding → Check Railway deployment
- Database errors → Verify database connectivity
- 500 errors → Check application logs

#### Integration Issues

- Frontend can't reach backend → Check CORS/networking
- Data not persisting → Check database connections
- Authentication issues → Verify auth configuration

## Best Practices

### Test Design

1. **Keep Tests Fast**: Sanity tests should complete quickly
2. **Focus on Critical Paths**: Test core user journeys
3. **Fail Fast**: Stop on first critical failure
4. **Clear Error Messages**: Make failures easy to understand

### Maintenance

1. **Update URLs**: Keep deployment URLs current
2. **Review Regularly**: Ensure tests still cover critical paths
3. **Monitor Performance**: Track test execution times
4. **Add New Tests**: Cover new critical functionality

### Troubleshooting

#### Test Environment Issues

```bash
# Clear test cache
rm -rf .pytest_cache

# Reinstall Playwright browsers
./venv/bin/playwright install

# Reset test database
rm -f test_sanity.db
```

#### Network Issues

```bash
# Test connectivity manually
curl -I https://marsel-to-do-list.vercel.app
curl -I https://your-railway-url.up.railway.app/docs

# Check DNS resolution
nslookup marsel-to-do-list.vercel.app
```

## Integration with Other Tests

Sanity tests complement other testing types:

| Test Type             | Purpose                | Frequency        | Duration |
| --------------------- | ---------------------- | ---------------- | -------- |
| **Unit Tests**        | Individual components  | Every commit     | Seconds  |
| **Integration Tests** | API endpoints          | Every commit     | Minutes  |
| **Sanity Tests**      | Critical functionality | Every deployment | Minutes  |
| **UI Tests**          | Complete user journeys | Nightly          | Minutes  |
| **Performance Tests** | System performance     | Weekly           | Hours    |

## Monitoring & Alerting

### Recommended Setup

1. **Automated Runs**: Every 15-30 minutes in production
2. **Slack/Email Alerts**: On any failure
3. **Dashboard**: Real-time sanity test status
4. **Escalation**: Page on-call for critical failures

### Example Monitoring Script

```bash
#!/bin/bash
# run_sanity_monitor.sh

while true; do
    ./run_sanity_tests.sh quick
    if [ $? -ne 0 ]; then
        # Send alert
        curl -X POST -H 'Content-type: application/json' \
             --data '{"text":"🚨 Sanity tests failed!"}' \
             $SLACK_WEBHOOK_URL
    fi
    sleep 1800  # 30 minutes
done
```

## Contributing

When adding new sanity tests:

1. Focus on **critical functionality** only
2. Keep tests **fast and reliable**
3. Use appropriate **markers**
4. Add **clear documentation**
5. Test with **different browsers** if UI-related
6. Ensure tests **clean up after themselves**

## Dependencies

- `pytest` - Test framework
- `pytest-html` - HTML reporting
- `requests` - HTTP client for API tests
- `playwright` - Browser automation for UI tests
- `pytest-playwright` - Playwright integration
- `fastapi[all]` - API framework (for local tests)

---

**Remember**: Sanity tests are your first line of defense against broken deployments. Keep them fast, reliable, and focused on critical functionality! 🛡️
