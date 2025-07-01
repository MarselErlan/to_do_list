import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app import crud, schemas

def get_auth_headers(client: TestClient, db: Session, username: str = "testsecureuser", password: str = "password123") -> dict:
    """Helper function to create a user, log in, and return auth headers."""
    # Create user if not exists
    if not crud.get_user_by_username(db, username):
        user_data = schemas.UserCreate(username=username, email=f"{username}@example.com", password=password)
        crud.create_user(db, user_data)
    
    # Log in to get token
    login_data = {"username": username, "password": password}
    response = client.post("/token", data=login_data)
    token = response.json()["access_token"]
    
    return {"Authorization": f"Bearer {token}"}

def test_create_todo_without_auth_fails(client: TestClient):
    """
    Test that creating a todo without authentication fails with a 401 error.
    """
    todo_data = {"title": "Unauthorized Todo"}
    response = client.post("/todos/", json=todo_data)
    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}

def test_create_and_get_todo_with_auth(client: TestClient, db: Session):
    """
    Test that a user can create and retrieve their own todo item when authenticated.
    """
    headers = get_auth_headers(client, db)
    
    # Create a todo
    todo_data = {"title": "My Authenticated Todo", "description": "It works!"}
    response = client.post("/todos/", json=todo_data, headers=headers)
    assert response.status_code == 200, response.text
    
    created_todo = response.json()
    assert created_todo["title"] == "My Authenticated Todo"
    assert "id" in created_todo
    
    # Get all todos for the authenticated user
    response = client.get("/todos/", headers=headers)
    assert response.status_code == 200
    
    todos = response.json()
    assert len(todos) >= 1
    assert "My Authenticated Todo" in [t["title"] for t in todos]

def test_user_cannot_see_other_users_todos(client: TestClient, db: Session):
    """
    Test that a user cannot see todos belonging to other users.
    """
    # 1. Create two users and get their auth headers
    user_one_headers = get_auth_headers(client, db, username="user_one", password="password1")
    user_two_headers = get_auth_headers(client, db, username="user_two", password="password2")

    # 2. User one creates a todo
    client.post("/todos/", json={"title": "User One's Todo"}, headers=user_one_headers)

    # 3. User two logs in and fetches todos
    response = client.get("/todos/", headers=user_two_headers)
    assert response.status_code == 200
    
    # 4. Assert that user two sees no todos
    assert response.json() == [] 