import pytest
from datetime import datetime, date, timedelta
from fastapi.testclient import TestClient

def test_create_todo_with_time_fields_api(client: TestClient):
    """Test creating a todo with time fields via API"""
    todo_data = {
        "title": "API Time Test",
        "description": "Testing time fields via API",
        "start_date": "2024-12-25",
        "start_time": "09:00:00",
        "end_date": "2024-12-25",
        "end_time": "10:30:00",
        "due_date": "2024-12-25"
    }
    
    response = client.post("/todos/", json=todo_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["title"] == "API Time Test"
    assert data["start_date"] == "2024-12-25"
    assert data["start_time"] == "09:00:00"
    assert data["end_date"] == "2024-12-25"
    assert data["end_time"] == "10:30:00"
    assert data["due_date"] == "2024-12-25"

def test_create_todo_without_time_fields_api(client: TestClient):
    """Test backward compatibility - creating todo without time fields"""
    todo_data = {
        "title": "Simple API Todo",
        "description": "No time fields"
    }
    
    response = client.post("/todos/", json=todo_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["title"] == "Simple API Todo"
    assert data["start_date"] is None
    assert data["start_time"] is None
    assert data["end_date"] is None
    assert data["end_time"] is None
    assert data["due_date"] is None

def test_get_todos_today_endpoint(client: TestClient):
    """Test GET /todos/today endpoint"""
    today = date.today()
    tomorrow = today + timedelta(days=1)
    
    # Create todos
    today_todo = {
        "title": "Today's API Task",
        "due_date": today.isoformat()
    }
    tomorrow_todo = {
        "title": "Tomorrow's API Task",
        "due_date": tomorrow.isoformat()
    }
    
    client.post("/todos/", json=today_todo)
    client.post("/todos/", json=tomorrow_todo)
    
    # Test today endpoint
    response = client.get("/todos/today")
    assert response.status_code == 200
    
    todos = response.json()
    today_titles = [todo["title"] for todo in todos]
    assert "Today's API Task" in today_titles
    assert "Tomorrow's API Task" not in today_titles

def test_get_todos_week_endpoint(client: TestClient):
    """Test GET /todos/week endpoint"""
    today = date.today()
    
    # Calculate this week and next week dates
    days_since_monday = today.weekday()
    week_start = today - timedelta(days=days_since_monday)
    next_week_date = week_start + timedelta(days=10)  # Next week
    
    # Create todos
    this_week_todo = {
        "title": "This Week API Task",
        "due_date": (week_start + timedelta(days=2)).isoformat()
    }
    next_week_todo = {
        "title": "Next Week API Task", 
        "due_date": next_week_date.isoformat()
    }
    
    client.post("/todos/", json=this_week_todo)
    client.post("/todos/", json=next_week_todo)
    
    # Test week endpoint
    response = client.get("/todos/week")
    assert response.status_code == 200
    
    todos = response.json()
    week_titles = [todo["title"] for todo in todos]
    assert "This Week API Task" in week_titles
    assert "Next Week API Task" not in week_titles

def test_get_todos_month_endpoint(client: TestClient):
    """Test GET /todos/month endpoint"""
    today = date.today()
    
    # Create todos for this month and next month
    this_month_todo = {
        "title": "This Month API Task",
        "due_date": today.replace(day=15).isoformat()
    }
    next_month_date = (today.replace(day=28) + timedelta(days=4)).replace(day=15)
    next_month_todo = {
        "title": "Next Month API Task",
        "due_date": next_month_date.isoformat()
    }
    
    client.post("/todos/", json=this_month_todo)
    client.post("/todos/", json=next_month_todo)
    
    # Test month endpoint
    response = client.get("/todos/month")
    assert response.status_code == 200
    
    todos = response.json()
    month_titles = [todo["title"] for todo in todos]
    assert "This Month API Task" in month_titles
    assert "Next Month API Task" not in month_titles

def test_get_todos_year_endpoint(client: TestClient):
    """Test GET /todos/year endpoint"""
    today = date.today()
    
    # Create todos for this year and next year
    this_year_todo = {
        "title": "This Year API Task",  
        "due_date": today.replace(month=6, day=15).isoformat()
    }
    next_year_todo = {
        "title": "Next Year API Task",
        "due_date": today.replace(year=today.year + 1, month=1, day=15).isoformat()
    }
    
    client.post("/todos/", json=this_year_todo)
    client.post("/todos/", json=next_year_todo)
    
    # Test year endpoint
    response = client.get("/todos/year")
    assert response.status_code == 200
    
    todos = response.json()
    year_titles = [todo["title"] for todo in todos]
    assert "This Year API Task" in year_titles
    assert "Next Year API Task" not in year_titles

def test_get_overdue_todos_endpoint(client: TestClient):
    """Test GET /todos/overdue endpoint"""
    today = date.today()
    yesterday = today - timedelta(days=1)
    tomorrow = today + timedelta(days=1)
    
    # Create todos
    overdue_todo = {
        "title": "Overdue API Task",
        "due_date": yesterday.isoformat(),
        "done": False
    }
    completed_overdue_todo = {
        "title": "Completed Overdue API Task",
        "due_date": yesterday.isoformat(),
        "done": True
    }
    future_todo = {
        "title": "Future API Task",
        "due_date": tomorrow.isoformat(),
        "done": False
    }
    
    client.post("/todos/", json=overdue_todo)
    client.post("/todos/", json=completed_overdue_todo)
    client.post("/todos/", json=future_todo)
    
    # Test overdue endpoint
    response = client.get("/todos/overdue")
    assert response.status_code == 200
    
    todos = response.json()
    overdue_titles = [todo["title"] for todo in todos]
    assert "Overdue API Task" in overdue_titles
    assert "Completed Overdue API Task" not in overdue_titles
    assert "Future API Task" not in overdue_titles

def test_update_todo_with_time_fields_api(client: TestClient):
    """Test updating a todo with time fields via API"""
    create_response = client.post("/todos/", json={"title": "Update Time Test"})
    todo_id = create_response.json()["id"]
    
    update_data = {
        "title": "Updated with Time API",
        "start_date": "2024-12-26",
        "start_time": "14:00:00",
        "due_date": "2024-12-26"
    }
    
    update_response = client.put(f"/todos/{todo_id}", json=update_data)
    assert update_response.status_code == 200
    
    data = update_response.json()
    assert data["title"] == "Updated with Time API"
    assert data["start_date"] == "2024-12-26"
    assert data["start_time"] == "14:00:00"
    assert data["due_date"] == "2024-12-26"

def test_get_todos_by_date_range_endpoint(client: TestClient):
    """Test GET /todos/range endpoint with date parameters"""
    today = date.today()
    start_date = today - timedelta(days=1)
    end_date = today + timedelta(days=1)
    
    # Create todos
    in_range_todo = {
        "title": "In Range Task",
        "due_date": today.isoformat()
    }
    out_of_range_todo = {
        "title": "Out of Range Task",
        "due_date": (today + timedelta(days=5)).isoformat()
    }
    
    client.post("/todos/", json=in_range_todo)
    client.post("/todos/", json=out_of_range_todo)
    
    # Test range endpoint
    response = client.get(f"/todos/range?start_date={start_date.isoformat()}&end_date={end_date.isoformat()}")
    assert response.status_code == 200
    
    todos = response.json()
    range_titles = [todo["title"] for todo in todos]
    assert "In Range Task" in range_titles
    assert "Out of Range Task" not in range_titles

def test_invalid_date_format_handling(client: TestClient):
    """Test API handles invalid date formats gracefully"""
    invalid_todo = {
        "title": "Invalid Date Test",
        "due_date": "invalid-date-format"
    }
    
    response = client.post("/todos/", json=invalid_todo)
    assert response.status_code == 422  # Validation error

def test_time_fields_in_response_format(client: TestClient):
    """Test that time fields are properly formatted in API responses"""
    todo_data = {
        "title": "Format Test",
        "start_date": "2024-12-25",
        "start_time": "09:00:00"
    }
    
    response = client.post("/todos/", json=todo_data)
    assert response.status_code == 200
    data = response.json()

    # Verify presence
    assert "start_date" in data
    assert "start_time" in data
    
    # Verify ISO format
    assert isinstance(data["start_date"], str)
    assert isinstance(data["start_time"], str)
    
    # Verify parseable
    from datetime import time, date
    date.fromisoformat(data["start_date"])
    time.fromisoformat(data["start_time"])
    
    assert data["start_date"] == "2024-12-25"
    assert data["start_time"] == "09:00:00" 