#!/bin/bash

# Sanity Test Runner Script for Todo App
# This script runs critical sanity tests to verify core functionality

echo "🧪 Starting Sanity Tests for Todo App"
echo "====================================="

# Set environment variables
export PYTHONPATH=.

# Load environment variables from .env file if it exists
if [ -f .env ]; then
    echo "🔑 Loading environment variables from .env file"
    source .env
fi

# Check if virtual environment is activated
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo "✅ Virtual environment detected: $VIRTUAL_ENV"
else
    echo "⚠️  No virtual environment detected. Activating venv..."
    source ./venv/bin/activate
fi

# Set default test mode
TEST_MODE=${1:-"local"}
BROWSER=${2:-"chromium"}

echo "🔍 Test mode: $TEST_MODE"
echo "🌐 Browser: $BROWSER (for UI tests)"

# Create reports directory
mkdir -p reports

echo ""
echo "🚀 Running sanity tests..."
echo ""

case $TEST_MODE in
    "local")
        echo "📍 Running LOCAL sanity tests (API only, no live deployments)"
        ./venv/bin/pytest tests/sanity/test_api_sanity.py::TestAPISanity \
            -v \
            -m "sanity and not live" \
            --html=reports/sanity_local_report.html \
            --self-contained-html
        ;;
    
    "api")
        echo "📍 Running API sanity tests (local + live API if available)"
        ./venv/bin/pytest tests/sanity/test_api_sanity.py \
            -v \
            -m "sanity" \
            --html=reports/sanity_api_report.html \
            --self-contained-html
        ;;
    
    "ui")
        echo "📍 Running UI sanity tests"
        ./venv/bin/pytest tests/sanity/test_ui_sanity.py::TestUISanity \
            -v \
            -m "sanity and ui" \
            --browser="$BROWSER" \
            --confcutdir=tests/sanity \
            --html=reports/sanity_ui_report.html \
            --self-contained-html
        ;;
    
    "integration")
        echo "📍 Running integration sanity tests (frontend + backend)"
        ./venv/bin/pytest tests/sanity/test_ui_sanity.py::TestFullStackSanity \
            -v \
            -m "sanity and integration" \
            --browser="$BROWSER" \
            --confcutdir=tests/sanity \
            --html=reports/sanity_integration_report.html \
            --self-contained-html
        ;;
    
    "deployment")
        echo "📍 Running deployment sanity tests"
        ./venv/bin/pytest tests/sanity/test_ui_sanity.py::TestDeploymentSanity \
            -v \
            -m "sanity and deployment" \
            --html=reports/sanity_deployment_report.html \
            --self-contained-html
        ;;
    
    "all"|"full")
        echo "📍 Running ALL sanity tests"
        ./venv/bin/pytest tests/sanity/ \
            -v \
            -m "sanity" \
            --browser="$BROWSER" \
            --html=reports/sanity_full_report.html \
            --self-contained-html
        ;;
    
    "quick")
        echo "📍 Running QUICK sanity tests (essential checks only)"
        ./venv/bin/pytest tests/sanity/ \
            -v \
            -m "sanity" \
            -k "health or loads or status" \
            --browser="$BROWSER" \
            --html=reports/sanity_quick_report.html \
            --self-contained-html
        ;;
    
    *)
        echo "❌ Invalid test mode: $TEST_MODE"
        echo ""
        echo "Available modes:"
        echo "  local       - Run local API tests only"
        echo "  api         - Run all API sanity tests"
        echo "  ui          - Run UI sanity tests"
        echo "  integration - Run frontend-backend integration tests"
        echo "  deployment  - Run deployment status tests"
        echo "  all|full    - Run all sanity tests"
        echo "  quick       - Run essential sanity checks only"
        echo ""
        echo "Usage: $0 [mode] [browser]"
        echo "Example: $0 quick chromium"
        exit 1
        ;;
esac

EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Sanity tests passed!"
    echo "🎉 Core functionality is working correctly"
else
    echo "❌ Sanity tests failed (exit code: $EXIT_CODE)"
    echo "⚠️  Critical functionality may be broken"
fi

echo "📊 Test report saved to: reports/sanity_${TEST_MODE}_report.html"
echo ""

# Show quick summary
if [ $EXIT_CODE -eq 0 ]; then
    echo "🚀 System Status: HEALTHY ✅"
else
    echo "🚨 System Status: NEEDS ATTENTION ❌"
fi

echo ""
exit $EXIT_CODE 