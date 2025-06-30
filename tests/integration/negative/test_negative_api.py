from fastapi.testclient import TestClient

def test_create_todo_invalid_payload(client: TestClient):
    # Test creating a to-do with no title (which is required)
    invalid_data = {"description": "This is missing a title"}
    response = client.post("/todos/", json=invalid_data)
    assert response.status_code == 422  # Unprocessable Entity

    # Test creating a to-do with the wrong data type for the title
    invalid_data = {"title": 123, "description": "Title is an int"}
    response = client.post("/todos/", json=invalid_data)
    assert response.status_code == 422


def test_get_non_existent_todo(client: TestClient):
    response = client.get("/todos/9999")
    assert response.status_code == 404


def test_update_non_existent_todo(client: TestClient):
    updated_data = {"title": "I will fail"}
    response = client.put("/todos/9999", json=updated_data)
    assert response.status_code == 404


def test_delete_non_existent_todo(client: TestClient):
    response = client.delete("/todos/9999")
    assert response.status_code == 404 