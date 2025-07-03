import sys
import os
import pytest

# Add project root to allow importing app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import crud
from app.schemas import UserCreate

def test_get_user_count(client, db):
    """
    Tests the user count endpoint.
    """
    # 1. Setup: Ensure the database is clean and then create a known number of users.
    # The test DB is clean at the start of each test thanks to our fixtures.
    db.query(crud.models.User).delete()
    db.commit()

    users_to_create = [
        UserCreate(username="count_user_1", email="cu1@example.com", password="p1"),
        UserCreate(username="count_user_2", email="cu2@example.com", password="p2"),
        UserCreate(username="count_user_3", email="cu3@example.com", password="p3"),
    ]

    for user in users_to_create:
        crud.create_user(db, user=user)

    # 2. Action: Call the new endpoint
    response = client.get("/users/count")

    # 3. Assertions
    assert response.status_code == 200
    assert response.json() == {"total_users": 3}

def test_delete_user_impact_on_sessions_and_todos(client, db):
    """
    Tests that when a user is deleted, their private session and associated todos are deleted,
    and their memberships and public todos in team sessions are handled correctly.
    """
    # 1. Create User1 (to be deleted) and User2 (collaborator) and log them in
    user1_data = {"username": "user_to_delete", "email": "delete@example.com", "password": "password"}
    user2_data = {"username": "collaborator_user", "email": "collab@example.com", "password": "password"}

    client.post("/users/", json=user1_data)
    client.post("/users/", json=user2_data)

    user1_login_response = client.post("/token", data={"username": "user_to_delete", "password": "password"})
    assert user1_login_response.status_code == 200
    user1_token = user1_login_response.json()["access_token"]
    user1_headers = {"Authorization": f"Bearer {user1_token}"}
    user1_obj = crud.get_user_by_username(db, username="user_to_delete")
    assert user1_obj

    user2_login_response = client.post("/token", data={"username": "collaborator_user", "password": "password"})
    assert user2_login_response.status_code == 200
    user2_token = user2_login_response.json()["access_token"]
    user2_headers = {"Authorization": f"Bearer {user2_token}"}
    user2_obj = crud.get_user_by_username(db, username="collaborator_user")
    assert user2_obj

    # 2. User1 creates a private todo
    private_todo_title = "User1 Private Todo"
    user1_private_todo_response = client.post("/todos/", json={"title": private_todo_title}, headers=user1_headers)
    assert user1_private_todo_response.status_code == 200
    user1_private_todo_id = user1_private_todo_response.json()["id"]
    user1_private_session_id = user1_private_todo_response.json()["session_id"]

    # 3. User1 creates a team session
    team_session_name = "Team for Deletion Test"
    team_session_response = client.post("/sessions/", json={"name": team_session_name}, headers=user1_headers)
    assert team_session_response.status_code == 200
    team_session_id = team_session_response.json()["id"]

    # 4. User1 invites User2 to the team session
    client.post(f"/sessions/{team_session_id}/invite", json={"email": user2_data["email"]}, headers=user1_headers)

    # 5. User1 creates a public todo in the team session
    user1_public_todo_title = "User1 Public Team Todo"
    user1_public_todo_response = client.post("/todos/", json={
        "title": user1_public_todo_title, "session_id": team_session_id
    }, headers=user1_headers)
    assert user1_public_todo_response.status_code == 200
    user1_public_todo_id = user1_public_todo_response.json()["id"]

    # 6. User2 creates a public todo in the team session
    user2_public_todo_title = "User2 Public Team Todo"
    user2_public_todo_response = client.post("/todos/", json={
        "title": user2_public_todo_title, "session_id": team_session_id
    }, headers=user2_headers)
    assert user2_public_todo_response.status_code == 200
    user2_public_todo_id = user2_public_todo_response.json()["id"]

    # Verify initial state: todos are present, user is member of team session
    assert crud.get_user(db, user1_obj.id)
    assert crud.get_todo(db, user1_private_todo_id)
    assert crud.get_todo(db, user1_public_todo_id)
    assert crud.get_session_member_by_user_and_session(db, team_session_id, user1_obj.id)
    assert crud.get_session(db, team_session_id) # The get_session function does not exist in crud.py, I will have to add it.

    # 7. User1 deletes their account
    delete_user_response = client.delete("/users/me", headers=user1_headers)
    assert delete_user_response.status_code == 200
    assert delete_user_response.json()["message"] == "User and associated data deleted successfully."

    # 8. Assertions after deletion
    # User1 should no longer exist
    assert crud.get_user(db, user1_obj.id) is None

    # User1's private todo and private session should be deleted
    assert crud.get_todo(db, user1_private_todo_id) is None
    assert crud.get_session(db, user1_private_session_id) is None

    # The team session created by User1 should be deleted (as User1 was the owner)
    assert crud.get_session(db, team_session_id) is None

    # User1's public todo in the team session should be deleted (cascade from session deletion)
    assert crud.get_todo(db, user1_public_todo_id) is None

    # User2's public todo in the team session should also be deleted (cascade from session deletion)
    assert crud.get_todo(db, user2_public_todo_id) is None

    # User2's membership in the deleted team session should be gone (implicitly by session deletion)
    assert crud.get_session_member_by_user_and_session(db, team_session_id, user2_obj.id) is None

    # User2 should still exist and their private session/todos should be unaffected
    assert crud.get_user(db, user2_obj.id) is not None
    user2_private_session = crud.get_private_session_for_user(db, user2_obj.id)
    assert user2_private_session is not None
    assert crud.get_todos_by_user(db, user2_obj.id) is not None # User2 should still have their private todos. 