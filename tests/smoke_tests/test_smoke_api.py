from fastapi.testclient import TestClient

def test_smoke_create_and_read_todo(client: TestClient):
    """
    A critical path test to ensure a to-do can be created and then read back.
    """
    todo_data = {"title": "Smoke Test Todo", "description": "Critical path test"}
    response = client.post("/todos/", json=todo_data)
    assert response.status_code == 200
    created_todo = response.json()
    todo_id = created_todo["id"]

    response = client.get(f"/todos/{todo_id}")
    assert response.status_code == 200
    retrieved_todo = response.json()
    assert retrieved_todo["id"] == todo_id

def test_smoke_get_non_existent_todo(client: TestClient):
    """
    A critical path test to ensure basic error handling is working.
    """
    response = client.get("/todos/9999")
    assert response.status_code == 404 