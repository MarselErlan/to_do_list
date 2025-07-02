import sys
import os
import pytest
from datetime import datetime, timedelta

# Add project root to allow importing app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import crud, models
from app.schemas import UserCreate
from app.security import get_password_hash

def test_request_password_reset_success(client, db, monkeypatch):
    """
    Tests that a registered user can successfully request a password reset code.
    """
    # Mock email sending
    async def mock_send_email(email_to: str, code: str):
        pass
    monkeypatch.setattr("app.main.send_verification_email", mock_send_email)
    
    # 1. Setup: Create a user
    user = UserCreate(username="reset_user", email="reset@example.com", password="old_password")
    crud.create_user(db, user)
    
    # 2. Action: Request a password reset
    response = client.post("/auth/forgot-password", json={"email": "reset@example.com"})

    # 3. Assertions
    assert response.status_code == 200
    assert response.json() == {"message": "Password reset code sent"}
    
    # Verify a code was created in the DB
    verification = crud.get_verification_code(db, email="reset@example.com")
    assert verification is not None

def test_request_password_reset_user_not_found(client, db):
    """
    Tests that requesting a reset for a non-existent email fails.
    """
    response = client.post("/auth/forgot-password", json={"email": "not_found@example.com"})
    assert response.status_code == 404
    assert response.json() == {"detail": "User with this email not found"}

def test_request_password_reset_rate_limit(client, db):
    """
    Tests that a user cannot request a password reset more than once every 5 hours.
    """
    # 1. Setup: Create user and an initial verification code created just now
    user = UserCreate(username="rate_limit_user", email="ratelimit@example.com", password="password")
    crud.create_user(db, user)
    
    # Manually create a recent verification entry
    recent_code = models.EmailVerification(
        email="ratelimit@example.com",
        code=get_password_hash("123456"),
        created_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(minutes=5)
    )
    db.add(recent_code)
    db.commit()

    # 2. Action: Immediately request another reset
    response = client.post("/auth/forgot-password", json={"email": "ratelimit@example.com"})
    
    # 3. Assertion: Should be rate-limited
    assert response.status_code == 429
    assert "Please wait before requesting another code" in response.json()["detail"]

def test_reset_password_success(client, db):
    """
    Tests that a user can successfully reset their password with a valid code.
    """
    # 1. Setup: Create user and a valid verification code
    email = "reset_success@example.com"
    username = "reset_success_user"
    old_password = "old_password"
    new_password = "new_password"
    
    crud.create_user(db, UserCreate(username=username, email=email, password=old_password))
    code = crud.create_verification_code(db, email=email)

    # 2. Action: Reset the password
    response = client.post(
        "/auth/reset-password",
        json={"email": email, "code": code, "new_password": new_password}
    )

    # 3. Assertions
    assert response.status_code == 200
    assert response.json() == {"message": "Password has been reset successfully"}

    # Verify the password was actually changed by trying to log in with the new password
    login_response = client.post("/token", data={"username": username, "password": new_password})
    assert login_response.status_code == 200
    assert "access_token" in login_response.json()

def test_reset_password_invalid_code(client, db):
    """
    Tests that password reset fails with an invalid verification code.
    """
    # 1. Setup
    email = "reset_fail@example.com"
    crud.create_user(db, UserCreate(username="reset_fail_user", email=email, password="password"))
    crud.create_verification_code(db, email=email) # This creates a valid code

    # 2. Action: Attempt to reset with an invalid code
    response = client.post(
        "/auth/reset-password",
        json={"email": email, "code": "000000", "new_password": "new_password"}
    )
    
    # 3. Assertions
    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid or expired verification code"} 