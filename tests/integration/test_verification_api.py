import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app import crud, models
from app.main import app
from app.database import SessionLocal

# Using the existing authenticated_client fixture from conftest
# It provides a client and a test user, but we need to manage the db session
# inside the test function to query the database for verification.

def test_request_verification_code(client, db, monkeypatch):
    """
    Test requesting a verification code for a new email, mocking the email sending.
    """
    # 1. Mock the email sending function
    async def mock_send_email(email_to: str, code: str):
        """A mock email function that does nothing."""
        pass

    monkeypatch.setattr("app.main.send_verification_email", mock_send_email)
    
    test_email = "new_user@example.com"
    
    response = client.post("/auth/request-verification", json={"email": test_email})
    
    # 2. Assert the API responds successfully
    assert response.status_code == 200
    assert response.json() == {"message": "Verification code sent successfully"}
    
    # 3. Assert the verification entry was created in the database
    verification_entry = db.query(models.EmailVerification).filter_by(email=test_email).first()
    assert verification_entry is not None
    assert verification_entry.email == test_email
    assert verification_entry.code is not None
    assert not verification_entry.verified
    
    db.close()

def test_register_user_with_valid_code(client, db):
    """
    Test registering a new user with a valid verification code.
    """
    test_email = "register_valid@example.com"
    test_username = "register_valid_user"
    test_password = "password123"

    # 1. First, get a valid code
    code = crud.create_verification_code(db, email=test_email)
    
    # 2. Attempt to register
    response = client.post(
        "/auth/register",
        json={
            "email": test_email,
            "code": code,
            "username": test_username,
            "password": test_password,
        },
    )
    
    # 3. Assert success
    assert response.status_code == 200
    token_data = response.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"
    
    # 4. Verify user was created
    user = crud.get_user_by_username(db, username=test_username)
    assert user is not None
    assert user.email == test_email

def test_register_user_with_invalid_code(client, db):
    """
    Test that user registration fails with an invalid verification code.
    """
    test_email = "register_invalid@example.com"
    crud.create_verification_code(db, email=test_email) # Creates a code in the DB

    response = client.post(
        "/auth/register",
        json={
            "email": test_email,
            "code": "000000", # Invalid code
            "username": "register_invalid_user",
            "password": "password123",
        },
    )
    
    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid or expired verification code"}

def test_register_user_with_expired_code(client, db):
    """
    Test that user registration fails if the verification code is expired.
    """
    test_email = "register_expired@example.com"
    
    # 1. Create a code that is already expired
    expired_code_entry = models.EmailVerification(
        email=test_email,
        code=crud.get_hashed_password("123456"),
        expires_at=datetime.utcnow() - timedelta(minutes=10) # Expired 10 mins ago
    )
    db.add(expired_code_entry)
    db.commit()

    # 2. Attempt to register
    response = client.post(
        "/auth/register",
        json={
            "email": test_email,
            "code": "123456",
            "username": "register_expired_user",
            "password": "password123",
        },
    )
    
    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid or expired verification code"} 