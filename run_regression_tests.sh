#!/bin/bash
set -e

echo "--- Running Regression Test Suite ---"

# Set necessary environment variables for the test run
export SECRET_KEY='test-secret'
export MAIL_USERNAME='testuser'
export MAIL_PASSWORD='testpassword'
export MAIL_FROM='test@example.com'
export MAIL_PORT=587
export MAIL_SERVER='smtp.test.com'
export MAIL_STARTTLS='True'
export MAIL_SSL_TLS='False'

# Run pytest on the entire tests directory
pytest tests/

echo "--- Regression Test Suite Finished ---" 