import pytest
from datetime import datetime, date, timedelta
from fastapi.testclient import TestClient

@pytest.mark.smoke
def test_smoke_time_management_workflow(client: TestClient):
    """Smoke test: Complete time management workflow"""
    today = date.today()
    tomorrow = today + timedelta(days=1)
    
    # Create a todo with time fields
    todo_data = {
        "title": "Smoke Test Time Todo",
        "description": "Testing time management",
        "start_time": "2024-12-25T09:00:00",
        "end_time": "2024-12-25T10:30:00",
        "due_date": today.isoformat()
    }
    
    # Create todo
    create_response = client.post("/todos/", json=todo_data)
    assert create_response.status_code == 200
    
    created_todo = create_response.json()
    assert created_todo["title"] == "Smoke Test Time Todo"
    assert created_todo["due_date"] == today.isoformat()
    
    # Test today endpoint
    today_response = client.get("/todos/today")
    assert today_response.status_code == 200
    today_todos = today_response.json()
    
    # Our todo should be in today's list
    todo_titles = [todo["title"] for todo in today_todos]
    assert "Smoke Test Time Todo" in todo_titles

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