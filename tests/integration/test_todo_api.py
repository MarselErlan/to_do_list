from fastapi.testclient import TestClient
from app import schemas, crud, models
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import pytest

def test_create_and_read_todo(authenticated_client: TestClient):
    # 1. Arrange: Define the to-do item data
    todo_data = {"title": "Integration Test Todo", "description": "This is a test"}

    # 2. Act: Create a to-do item
    response = authenticated_client.post("/todos/", json=todo_data)

    # 3. Assert: Check the creation response
    assert response.status_code == 200
    created_todo = response.json()
    assert created_todo["title"] == todo_data["title"]
    assert created_todo["description"] == todo_data["description"]
    assert "id" in created_todo

    todo_id = created_todo["id"]

    # 4. Act: Retrieve the to-do item
    response = authenticated_client.get(f"/todos/{todo_id}")

    # 5. Assert: Check the retrieval response
    assert response.status_code == 200
    retrieved_todo = response.json()
    assert retrieved_todo["title"] == todo_data["title"]
    assert retrieved_todo["id"] == todo_id


def test_update_todo(authenticated_client: TestClient):
    # Arrange: Create a to-do to update
    initial_data = {"title": "To be updated", "description": "Initial description"}
    response = authenticated_client.post("/todos/", json=initial_data)
    assert response.status_code == 200
    todo_id = response.json()["id"]

    # Act: Update the to-do
    updated_data = {"title": "Updated Title", "description": "Updated Description", "done": True}
    response = authenticated_client.put(f"/todos/{todo_id}", json=updated_data)

    # Assert: Check the update response
    assert response.status_code == 200
    updated_todo = response.json()
    assert updated_todo["title"] == updated_data["title"]
    assert updated_todo["description"] == updated_data["description"]
    assert updated_todo["done"] is True

    # Verify the update was persisted
    response = authenticated_client.get(f"/todos/{todo_id}")
    assert response.status_code == 200
    assert response.json()["title"] == updated_data["title"]


def test_delete_todo(authenticated_client: TestClient):
    # Arrange: Create a to-do to delete
    initial_data = {"title": "To be deleted", "description": "Delete me"}
    response = authenticated_client.post("/todos/", json=initial_data)
    assert response.status_code == 200
    todo_id = response.json()["id"]

    # Act: Delete the to-do
    response = authenticated_client.delete(f"/todos/{todo_id}")

    # Assert: Check the delete response
    assert response.status_code == 200
    assert response.json()["id"] == todo_id

    # Verify the to-do was deleted
    response = authenticated_client.get(f"/todos/{todo_id}")
    assert response.status_code == 404

def test_get_all_todos_for_user(authenticated_client: TestClient):
    """
    Test retrieving all todos for an authenticated user.
    """
    # Arrange: Create multiple todos for the authenticated user
    todo_data1 = {"title": "User Todo 1", "description": "First todo"}
    todo_data2 = {"title": "User Todo 2", "description": "Second todo"}
    
    authenticated_client.post("/todos/", json=todo_data1)
    authenticated_client.post("/todos/", json=todo_data2)

    # Act: Retrieve all todos
    response = authenticated_client.get("/todos/")

    # Assert: Check the response
    assert response.status_code == 200
    todos = response.json()
    assert isinstance(todos, list)
    assert len(todos) >= 2 # Should have at least the two we just created, plus any others from other tests
    
    # Check if the created todos are in the list
    titles = [todo["title"] for todo in todos]
    assert todo_data1["title"] in titles
    assert todo_data2["title"] in titles

def test_todo_visibility_global_public(authenticated_client: TestClient, db):
    """
    Test creating a global public todo and ensure it's accessible.
    This test will check if a todo marked as is_global_public can be retrieved
    without specific user context, although the /todos/ endpoint is user-specific.
    It's more about ensuring the flag is set correctly and the CRUD functions
    can handle it.
    """
    # Arrange: Create a global public todo
    public_todo_data = {
        "title": "Global Public Todo",
        "description": "This todo is public globally",
        "is_global_public": True
    }
    response = authenticated_client.post("/todos/", json=public_todo_data)
    assert response.status_code == 200
    public_todo_id = response.json()["id"]

    # Act: Retrieve the public todo by its ID
    # This endpoint is user-specific, so the authenticated_client should be able to see its own global public todo.
    response = authenticated_client.get(f"/todos/{public_todo_id}")

    # Assert: Check if the public todo is retrieved successfully
    assert response.status_code == 200
    retrieved_public_todo = response.json()
    assert retrieved_public_todo["title"] == public_todo_data["title"]
    assert retrieved_public_todo["is_global_public"] is True

    # To fully test global public visibility, one would ideally need an unauthenticated client
    # or a different user's client to try and access it via a general "public todos" endpoint,
    # which is not explicitly available in the current API or within the scope of test_todo_api.py.
    # The current test verifies the flag is correctly set and retrievable by the owner. 

def test_create_private_todo_in_team_session(authenticated_client: TestClient, db: Session):
    """
    Test creating a private todo within a team session and verifying its visibility.
    """
    # Arrange: Create a team session and get the owner's ID
    session_create_data = schemas.SessionCreate(name="Private Team Session Test")
    
    # Get the authenticated user's ID
    current_user_response = authenticated_client.get("/users/me")
    assert current_user_response.status_code == 200
    owner_id = current_user_response.json()["id"]

    team_session = crud.create_team_session(db, session=session_create_data, owner_id=owner_id)
    assert team_session is not None

    # Create a private todo within this session
    private_todo_data = {
        "title": "Team Private Todo",
        "description": "Only visible to owner in team",
        "session_id": team_session.id,
        "is_private": True
    }
    response = authenticated_client.post("/todos/", json=private_todo_data)
    assert response.status_code == 200
    created_todo = response.json()
    assert created_todo["title"] == private_todo_data["title"]
    assert created_todo["session_id"] == team_session.id
    assert created_todo["is_private"] is True

    # Verify the todo is visible to the owner (the creator)
    response = authenticated_client.get(f"/todos/{created_todo['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == created_todo["id"]

    # --- Now, verify it's NOT visible to another member of the session (if implemented) ---
    # This requires creating another user and inviting them to the session,
    # then using their client to try and view the todo.
    # For simplicity, we'll assume the /todos/{id} endpoint respects private flag
    # and only accessible by owner, even if in a session.
    # A more robust test would involve a second authenticated_client for a different user
    # and testing visibility via /sessions/{session_id}/todos.

def test_create_global_public_todo_in_team_session(authenticated_client: TestClient, db: Session):
    """
    Test creating a global public todo within a team session and verifying its visibility.
    """
    # Arrange: Create a team session and get the owner's ID
    session_create_data = schemas.SessionCreate(name="Global Public Team Session Test")

    # Get the authenticated user's ID
    current_user_response = authenticated_client.get("/users/me")
    assert current_user_response.status_code == 200
    owner_id = current_user_response.json()["id"]

    team_session = crud.create_team_session(db, session=session_create_data, owner_id=owner_id)
    assert team_session is not None

    # Create a global public todo within this session
    global_public_todo_data = {
        "title": "Team Global Public Todo",
        "description": "Visible to everyone including outside team",
        "session_id": team_session.id,
        "is_global_public": True
    }
    response = authenticated_client.post("/todos/", json=global_public_todo_data)
    assert response.status_code == 200
    created_todo = response.json()
    assert created_todo["title"] == global_public_todo_data["title"]
    assert created_todo["session_id"] == team_session.id
    assert created_todo["is_global_public"] is True

    # Verify the todo is visible to the owner (the creator)
    response = authenticated_client.get(f"/todos/{created_todo['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == created_todo["id"]

    # To fully test global public visibility, one would ideally need an unauthenticated client
    # or a different user's client to try and access it via a general "public todos" endpoint,
    # which is not explicitly available in the current API or within the scope of test_todo_api.py.
    # The current test verifies the flag is correctly set and retrievable by the owner.
    # For full collaboration scenario testing (e.g., another team member seeing it),
    # consider test_session_api.py or a dedicated collaboration test file.

def test_create_private_todo_in_personal_workspace(authenticated_client: TestClient, db: Session):
    """
    Test creating a private todo in the user's personal workspace (no session_id provided).
    This should default to is_private=True.
    """
    # Arrange: Todo data without session_id and is_private explicitly set
    private_personal_todo_data = {
        "title": "Personal Private Todo",
        "description": "Should be private by default in personal workspace"
    }
    response = authenticated_client.post("/todos/", json=private_personal_todo_data)
    assert response.status_code == 200
    created_todo = response.json()
    assert created_todo["title"] == private_personal_todo_data["title"]
    assert created_todo["session_id"] is not None # Should be assigned to the user's private session
    assert created_todo["is_private"] is True
    assert created_todo["is_global_public"] is False # Explicitly false as it's private

    # Verify retrieval by owner
    response = authenticated_client.get(f"/todos/{created_todo['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == created_todo["id"]

def test_create_global_public_todo_in_personal_workspace(authenticated_client: TestClient, db: Session):
    """
    Test creating a global public todo in the user's personal workspace (no session_id provided).
    This should set is_global_public=True and is_private=False.
    """
    # Arrange: Todo data for a global public todo in personal workspace
    global_public_personal_todo_data = {
        "title": "Personal Global Public Todo",
        "description": "Should be globally public and not private",
        "is_global_public": True
    }
    response = authenticated_client.post("/todos/", json=global_public_personal_todo_data)
    assert response.status_code == 200
    created_todo = response.json()
    assert created_todo["title"] == global_public_personal_todo_data["title"]
    assert created_todo["session_id"] is not None # Should be assigned to the user's private session
    assert created_todo["is_private"] is False # Global public implies not private
    assert created_todo["is_global_public"] is True

    # Verify retrieval by owner
    response = authenticated_client.get(f"/todos/{created_todo['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == created_todo["id"]