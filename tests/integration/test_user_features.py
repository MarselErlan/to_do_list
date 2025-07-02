from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app import crud, schemas

def test_forgot_username_success(client: TestClient, db: Session):
    """
    Test successfully retrieving a username given a valid email.
    """
    # Step 1: Create a user in the database to test against
    user_in = schemas.UserCreate(
        username="testuser_for_forgot_feature",
        email="forgot.username@example.com",
        password="testpassword"
    )
    crud.create_user(db=db, user=user_in)

    # Step 2: Make a request to the new endpoint
    response = client.post(
        "/users/forgot-username",
        json={"email": "forgot.username@example.com"}
    )

    # Step 3: Assert the response is correct
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser_for_forgot_feature"

def test_forgot_username_not_found(client: TestClient):
    """
    Test the case where the email does not exist in the database.
    """
    response = client.post(
        "/users/forgot-username",
        json={"email": "nonexistent.user@example.com"}
    )
    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "User with this email not found" 