import pytest
from datetime import datetime, date, timedelta
from fastapi.testclient import TestClient

@pytest.mark.smoke
def test_smoke_time_management_workflow(client: TestClient):
    """Smoke test: Complete time management workflow"""
    today = date.today()

    # Create a todo with time fields
    todo_data = {
        "title": "Smoke Test Time Todo",
        "description": "Testing time management",
        "start_date": today.isoformat(),
        "start_time": "09:00:00",
        "due_date": today.isoformat()
    }

    # Create todo
    create_response = client.post("/todos/", json=todo_data)
    assert create_response.status_code == 200
    todo_id = create_response.json()["id"]

    # Verify retrieval
    get_response = client.get(f"/todos/{todo_id}")
    assert get_response.status_code == 200
    retrieved_data = get_response.json()
    assert retrieved_data["start_date"] == today.isoformat()
    assert retrieved_data["start_time"] == "09:00:00"

    # Verify it appears in today's list
    today_response = client.get("/todos/today")
    assert today_response.status_code == 200
    assert any(todo["id"] == todo_id for todo in today_response.json())

@pytest.mark.smoke
def test_smoke_overdue_detection(client: TestClient):
    """Smoke test: Overdue todo detection"""
    yesterday = date.today() - timedelta(days=1)
    
    # Create overdue todo
    overdue_todo = {
        "title": "Smoke Test Overdue",
        "description": "This should be overdue",
        "due_date": yesterday.isoformat(),
        "done": False
    }
    
    create_response = client.post("/todos/", json=overdue_todo)
    assert create_response.status_code == 200
    
    # Test overdue endpoint
    overdue_response = client.get("/todos/overdue")
    assert overdue_response.status_code == 200
    
    overdue_todos = overdue_response.json()
    overdue_titles = [todo["title"] for todo in overdue_todos]
    assert "Smoke Test Overdue" in overdue_titles 