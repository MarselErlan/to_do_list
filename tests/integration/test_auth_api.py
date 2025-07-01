import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app import crud, schemas

def test_login_for_access_token(client: TestClient, db: Session):
    """
    Test that a user can log in with a username and password to get a JWT access token.
    """
    # 1. Create a user in the database first
    user_data = schemas.UserCreate(
        username="testloginuser",
        email="testlogin@example.com",
        password="password123"
    )
    crud.create_user(db, user_data)

    # 2. Attempt to log in with the user's credentials
    login_data = {
        "username": "testloginuser",
        "password": "password123"
    }
    response = client.post("/token", data=login_data)

    # 3. Assert a successful response and token format
    assert response.status_code == 200, response.text
    
    token = response.json()
    assert "access_token" in token
    assert token["token_type"] == "bearer"

def test_create_user_signup(client: TestClient, db: Session):
    """
    Test that a new user can be created via a public sign-up endpoint.
    """
    signup_data = {
        "username": "signupuser",
        "email": "signup@example.com",
        "password": "password123"
    }

    response = client.post("/users/", json=signup_data)

    # Assert that the request was successful and the user was created
    assert response.status_code == 200, response.text
    
    data = response.json()
    assert data["username"] == "signupuser"
    assert data["email"] == "signup@example.com"
    assert "id" in data
    assert "hashed_password" not in data # Ensure password is not returned

    # Verify the user exists in the database
    user_in_db = crud.get_user_by_username(db, username="signupuser")
    assert user_in_db is not None
    assert user_in_db.email == "signup@example.com"

def test_create_user_duplicate_username(client: TestClient, db: Session):
    """
    Test that the API returns a 400 error if the username is already taken.
    """
    # Create an initial user
    client.post("/users/", json={
        "username": "duplicateuser",
        "email": "unique1@example.com",
        "password": "password123"
    })

    # Attempt to create a user with the same username
    response = client.post("/users/", json={
        "username": "duplicateuser",
        "email": "unique2@example.com",
        "password": "password456"
    })

    assert response.status_code == 400
    assert response.json() == {"detail": "Username already registered"}

def test_create_user_duplicate_email(client: TestClient, db: Session):
    """
    Test that the API returns a 400 error if the email is already taken.
    """
    # Create an initial user
    client.post("/users/", json={
        "username": "user1",
        "email": "duplicate@example.com",
        "password": "password123"
    })

    # Attempt to create a user with the same email
    response = client.post("/users/", json={
        "username": "user2",
        "email": "duplicate@example.com",
        "password": "password456"
    })

    assert response.status_code == 400
    assert response.json() == {"detail": "Email already registered"} 