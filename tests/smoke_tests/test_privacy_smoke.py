"""
Smoke tests for privacy and visibility features.
These tests ensure data security and proper access controls work.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


def create_user_and_get_headers(client: TestClient, username: str) -> dict:
    """Helper to create user and get auth headers."""
    user_data = {"username": username, "email": f"{username}@test.com", "password": "pass"}
    client.post("/users/", json=user_data)
    
    token_response = client.post("/token", data={"username": username, "password": "pass"})
    token = token_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.smoke
def test_smoke_private_todo_isolation(client: TestClient, db: Session):
    """
    Critical path: Private todos are properly isolated between users
    """
    # Create two users
    user1_headers = create_user_and_get_headers(client, "smoke_user1")
    user2_headers = create_user_and_get_headers(client, "smoke_user2")
    
    # User 1 creates a private todo
    private_todo = {"title": "User1 Private Todo", "is_private": True}
    response = client.post("/todos/", json=private_todo, headers=user1_headers)
    assert response.status_code == 200
    
    # User 2 should not see User 1's private todo
    response = client.get("/todos/", headers=user2_headers)
    assert response.status_code == 200
    
    user2_todos = response.json()
    user1_todo_titles = [todo["title"] for todo in user2_todos]
    assert "User1 Private Todo" not in user1_todo_titles


@pytest.mark.smoke  
def test_smoke_global_public_todo_visibility(client: TestClient, db: Session):
    """
    Critical path: Global public todos are visible across teams
    """
    # Create two users in different teams
    user1_headers = create_user_and_get_headers(client, "smoke_global1")
    user2_headers = create_user_and_get_headers(client, "smoke_global2")
    
    # User 1 creates a global public todo
    global_todo = {
        "title": "Global Announcement", 
        "description": "Important company-wide update",
        "is_global_public": True
    }
    response = client.post("/todos/", json=global_todo, headers=user1_headers)
    assert response.status_code == 200
    
    # User 2 should see the global public todo
    response = client.get("/todos/", headers=user2_headers)
    assert response.status_code == 200
    
    user2_todos = response.json()
    global_todo_titles = [todo["title"] for todo in user2_todos]
    assert "Global Announcement" in global_todo_titles


@pytest.mark.smoke
def test_smoke_team_todo_visibility(client: TestClient, db: Session):
    """
    Critical path: Team todos are visible to team members only
    """
    # Create owner and collaborator
    owner_headers = create_user_and_get_headers(client, "smoke_owner")
    member_headers = create_user_and_get_headers(client, "smoke_member") 
    outsider_headers = create_user_and_get_headers(client, "smoke_outsider")
    
    # Owner creates team session and invites member
    session_response = client.post("/sessions/", json={"name": "Smoke Team"}, headers=owner_headers)
    session_id = session_response.json()["id"]
    
    client.post(f"/sessions/{session_id}/invite", 
                json={"email": "smoke_member@test.com"}, 
                headers=owner_headers)
    
    # Owner creates team todo
    team_todo = {
        "title": "Team Project Todo",
        "session_id": session_id,
        "is_private": False  # Public within team
    }
    response = client.post("/todos/", json=team_todo, headers=owner_headers)
    assert response.status_code == 200
    
    # Team member should see it
    response = client.get("/todos/", headers=member_headers)
    member_todos = [todo["title"] for todo in response.json()]
    assert "Team Project Todo" in member_todos
    
    # Outsider should NOT see it
    response = client.get("/todos/", headers=outsider_headers)
    outsider_todos = [todo["title"] for todo in response.json()]
    assert "Team Project Todo" not in outsider_todos 