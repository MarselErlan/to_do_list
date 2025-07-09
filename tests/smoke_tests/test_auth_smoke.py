"""
Smoke tests for authentication and user management critical paths.
These tests ensure the basic user lifecycle works correctly.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app import crud


@pytest.mark.smoke
def test_smoke_user_registration_and_login(client: TestClient, db: Session):
    """
    Critical path: User can register and immediately log in
    """
    # Registration
    user_data = {
        "username": "smoke_auth_user", 
        "email": "smoke_auth@test.com", 
        "password": "smokepass123"
    }
    
    register_response = client.post("/users/", json=user_data)
    assert register_response.status_code == 200
    
    # Immediate login
    login_response = client.post("/token", data={
        "username": "smoke_auth_user", 
        "password": "smokepass123"
    })
    assert login_response.status_code == 200
    
    token_data = login_response.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"


@pytest.mark.smoke  
def test_smoke_protected_endpoint_access(client: TestClient, db: Session):
    """
    Critical path: Authentication protects endpoints correctly
    """
    # Attempt to access protected endpoint without auth
    response = client.get("/todos/")
    assert response.status_code == 401
    
    # Create user and get token
    user_data = {"username": "smoke_protected", "email": "smoke_protected@test.com", "password": "pass"}
    client.post("/users/", json=user_data)
    
    token_response = client.post("/token", data={"username": "smoke_protected", "password": "pass"})
    token = token_response.json()["access_token"]
    
    # Access protected endpoint with auth
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/todos/", headers=headers)
    assert response.status_code == 200


@pytest.mark.smoke
def test_smoke_user_gets_private_session(client: TestClient, db: Session):
    """
    Critical path: New users automatically get a private session
    """
    # Create user
    user_data = {"username": "smoke_session_user", "email": "smoke_session@test.com", "password": "pass"}
    register_response = client.post("/users/", json=user_data)
    assert register_response.status_code == 200
    
    # Login and check sessions
    token_response = client.post("/token", data={"username": "smoke_session_user", "password": "pass"})
    token = token_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    sessions_response = client.get("/sessions/", headers=headers)
    assert sessions_response.status_code == 200
    
    sessions = sessions_response.json()
    assert len(sessions) >= 1  # Should have at least private session
    
    # Check private session exists (name is None)
    has_private_session = any(session["name"] is None for session in sessions)
    assert has_private_session 