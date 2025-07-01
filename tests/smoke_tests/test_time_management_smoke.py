import pytest
from datetime import datetime, date, timedelta
from fastapi.testclient import TestClient
from app import crud, schemas
from sqlalchemy.orm import Session

def get_auth_headers(client: TestClient, db: Session, username: str, password: str) -> dict:
    """Helper to get auth headers for a user."""
    if not crud.get_user_by_username(db, username):
        user_data = schemas.UserCreate(username=username, email=f"{username}@example.com", password=password)
        crud.create_user(db, user_data)
    
    response = client.post("/token", data={"username": username, "password": password})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.mark.smoke
def test_smoke_time_management_workflow(client: TestClient, db: Session):
    """Smoke test: Complete time management workflow"""
    headers = get_auth_headers(client, db, "smoke_user", "smokepass")
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
    create_response = client.post("/todos/", json=todo_data, headers=headers)
    assert create_response.status_code == 200
    todo_id = create_response.json()["id"]

    # Verify retrieval
    get_response = client.get(f"/todos/{todo_id}", headers=headers)
    assert get_response.status_code == 200
    retrieved_data = get_response.json()
    assert retrieved_data["start_date"] == today.isoformat()
    assert retrieved_data["start_time"] == "09:00:00"

    # Verify it appears in today's list
    today_response = client.get("/todos/today", headers=headers)
    assert today_response.status_code == 200
    assert any(todo["id"] == todo_id for todo in today_response.json())

@pytest.mark.smoke
def test_smoke_overdue_detection(client: TestClient, db: Session):
    """Smoke test: Overdue todo detection"""
    headers = get_auth_headers(client, db, "smoke_overdue_user", "overduepass")
    yesterday = date.today() - timedelta(days=1)
    
    # Create overdue todo
    overdue_todo = {
        "title": "Smoke Test Overdue",
        "description": "This should be overdue",
        "due_date": yesterday.isoformat(),
        "done": False
    }
    
    create_response = client.post("/todos/", json=overdue_todo, headers=headers)
    assert create_response.status_code == 200
    
    # Test overdue endpoint
    overdue_response = client.get("/todos/overdue", headers=headers)
    assert overdue_response.status_code == 200
    
    overdue_todos = overdue_response.json()
    overdue_titles = [todo["title"] for todo in overdue_todos]
    assert "Smoke Test Overdue" in overdue_titles 