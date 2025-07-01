#!/bin/bash
set -e

echo "--- Running Regression Test Suite ---"

# Activate virtual environment
source venv/bin/activate

# Set PYTHONPATH to include the app directory
export PYTHONPATH=$PYTHONPATH:.

# Set the live API URL for the tests
export LIVE_API_URL="https://web-production-56fee.up.railway.app"

# Run only the tests marked as "regression"
pytest -m regression -v

echo "--- Regression Test Suite Finished ---" 