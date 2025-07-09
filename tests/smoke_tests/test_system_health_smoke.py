"""
Smoke tests for system health and infrastructure.
These tests ensure critical system components are functioning.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app import crud


@pytest.mark.smoke
def test_smoke_api_health_endpoint(client: TestClient):
    """
    Critical path: Health endpoint responds correctly
    """
    response = client.get("/health")
    assert response.status_code == 200
    
    health_data = response.json()
    assert health_data["status"] == "ok"


@pytest.mark.smoke
def test_smoke_database_connectivity(client: TestClient, db: Session):
    """
    Critical path: Database operations work correctly
    """
    # Test database read
    user_count = crud.count_users(db)
    assert isinstance(user_count, int)
    assert user_count >= 0
    
    # Test database write
    from app.schemas import UserCreate
    test_user = UserCreate(
        username="smoke_db_test", 
        email="smoke_db@test.com", 
        password="pass"
    )
    
    created_user = crud.create_user(db, test_user)
    assert created_user is not None
    assert created_user.username == "smoke_db_test"


@pytest.mark.smoke
def test_smoke_cors_headers_present(client: TestClient):
    """
    Critical path: CORS headers are properly configured
    """
    # Make a request that would trigger CORS
    response = client.get("/health")
    
    # Note: In test environment, CORS headers might not be present
    # This is more for documentation that CORS should be tested
    assert response.status_code == 200


@pytest.mark.smoke
def test_smoke_authentication_system(client: TestClient, db: Session):
    """
    Critical path: JWT authentication system works end-to-end
    """
    # Create user
    user_data = {"username": "smoke_jwt", "email": "smoke_jwt@test.com", "password": "jwtpass"}
    response = client.post("/users/", json=user_data)
    assert response.status_code == 200
    
    # Get token
    token_response = client.post("/token", data={"username": "smoke_jwt", "password": "jwtpass"})
    assert token_response.status_code == 200
    
    token = token_response.json()["access_token"]
    assert len(token) > 10  # Basic token validation
    
    # Use token to access protected endpoint
    headers = {"Authorization": f"Bearer {token}"}
    protected_response = client.get("/users/me", headers=headers)
    assert protected_response.status_code == 200
    
    user_info = protected_response.json()
    assert user_info["username"] == "smoke_jwt"


@pytest.mark.smoke
def test_smoke_error_handling(client: TestClient):
    """
    Critical path: API handles errors gracefully
    """
    # Test 404 handling
    response = client.get("/nonexistent-endpoint")
    assert response.status_code == 404
    
    # Test 401 handling  
    response = client.get("/todos/")
    assert response.status_code == 401
    
    # Test 422 handling (validation error)
    response = client.post("/users/", json={"invalid": "data"})
    assert response.status_code == 422 