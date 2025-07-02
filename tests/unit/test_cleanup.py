import sys
import os
import pytest
from datetime import datetime, timedelta

# Add project root to allow importing app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import crud, models
from app.security import get_password_hash

def test_cleanup_expired_codes(db):
    """
    Tests that the cleanup function correctly removes only the codes
    that are both expired and unverified.
    """
    # 1. Setup: Create various code entries in the database
    
    # - An expired code (should be deleted)
    expired_code = models.EmailVerification(
        email="expired@example.com",
        code=get_password_hash("111111"),
        expires_at=datetime.utcnow() - timedelta(minutes=10)
    )
    
    # - An active, unverified code (should NOT be deleted)
    active_code = models.EmailVerification(
        email="active@example.com",
        code=get_password_hash("222222"),
        expires_at=datetime.utcnow() + timedelta(minutes=10)
    )

    # - An expired but already verified code (should NOT be deleted)
    verified_expired_code = models.EmailVerification(
        email="verified_expired@example.com",
        code=get_password_hash("333333"),
        expires_at=datetime.utcnow() - timedelta(minutes=10),
        verified=True
    )
    
    db.add_all([expired_code, active_code, verified_expired_code])
    db.commit()

    # 2. Action: Run the cleanup function (this function doesn't exist yet)
    deleted_count = crud.cleanup_expired_codes(db)
    
    # 3. Assertions
    assert deleted_count == 1
    
    # Verify the correct records are in the DB
    all_codes = db.query(models.EmailVerification).all()
    assert len(all_codes) == 2
    
    remaining_emails = {code.email for code in all_codes}
    assert "expired@example.com" not in remaining_emails
    assert "active@example.com" in remaining_emails
    assert "verified_expired@example.com" in remaining_emails 