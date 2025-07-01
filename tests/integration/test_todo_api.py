from fastapi.testclient import TestClient
from app import schemas

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