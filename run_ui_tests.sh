#!/bin/bash

# UI Test Runner Script for Todo App
# This script runs Playwright UI tests against the live todo application

echo "🎭 Starting UI Tests for Todo App"
echo "================================="

# Set environment variables
export PYTHONPATH=.

# Check if virtual environment is activated
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo "✅ Virtual environment detected: $VIRTUAL_ENV"
else
    echo "⚠️  No virtual environment detected. Activating venv..."
    source ./venv/bin/activate
fi

# Default browser (can be overridden)
BROWSER=${1:-chromium}
echo "🌐 Browser: $BROWSER"

# Default test path (can be overridden)
TEST_PATH=${2:-tests/ui/}
echo "📁 Test path: $TEST_PATH"

echo ""
echo "🚀 Running UI tests..."
echo ""

# Run the tests
./venv/bin/pytest "$TEST_PATH" \
    -v \
    --browser="$BROWSER" \
    --html=reports/ui_test_report.html \
    --self-contained-html \
    -m ui

EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ All UI tests passed!"
else
    echo "❌ Some UI tests failed (exit code: $EXIT_CODE)"
fi

echo "📊 Test report saved to: reports/ui_test_report.html"
echo ""

exit $EXIT_CODE 