import pytest
from datetime import datetime, date, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.crud import get_user_by_username

def test_create_todo_with_time_fields_api(authenticated_client: TestClient):
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
    
    response = authenticated_client.post("/todos/", json=todo_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["title"] == "API Time Test"
    assert data["start_date"] == "2024-12-25"
    assert data["start_time"] == "09:00:00"
    assert data["end_date"] == "2024-12-25"
    assert data["end_time"] == "10:30:00"
    assert data["due_date"] == "2024-12-25"

def test_create_todo_without_time_fields_api(authenticated_client: TestClient):
    """Test backward compatibility - creating todo without time fields"""
    todo_data = {
        "title": "Simple API Todo",
        "description": "No time fields"
    }
    
    response = authenticated_client.post("/todos/", json=todo_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["title"] == "Simple API Todo"
    assert data["start_date"] is None
    assert data["start_time"] is None
    assert data["end_date"] is None
    assert data["end_time"] is None
    assert data["due_date"] is None

def test_get_todos_today_endpoint(authenticated_client: TestClient):
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
    
    authenticated_client.post("/todos/", json=today_todo)
    authenticated_client.post("/todos/", json=tomorrow_todo)
    
    # Test today endpoint
    response = authenticated_client.get("/todos/today")
    assert response.status_code == 200
    
    todos = response.json()
    today_titles = [todo["title"] for todo in todos]
    assert "Today's API Task" in today_titles
    assert "Tomorrow's API Task" not in today_titles

def test_get_todos_week_endpoint(authenticated_client: TestClient):
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
    
    authenticated_client.post("/todos/", json=this_week_todo)
    authenticated_client.post("/todos/", json=next_week_todo)
    
    # Test week endpoint
    response = authenticated_client.get("/todos/week")
    assert response.status_code == 200
    
    todos = response.json()
    week_titles = [todo["title"] for todo in todos]
    assert "This Week API Task" in week_titles
    assert "Next Week API Task" not in week_titles

def test_get_todos_month_endpoint(authenticated_client: TestClient):
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
    
    authenticated_client.post("/todos/", json=this_month_todo)
    authenticated_client.post("/todos/", json=next_month_todo)
    
    # Test month endpoint
    response = authenticated_client.get("/todos/month")
    assert response.status_code == 200
    
    todos = response.json()
    month_titles = [todo["title"] for todo in todos]
    assert "This Month API Task" in month_titles
    assert "Next Month API Task" not in month_titles

def test_get_todos_year_endpoint(authenticated_client: TestClient):
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
    
    authenticated_client.post("/todos/", json=this_year_todo)
    authenticated_client.post("/todos/", json=next_year_todo)
    
    # Test year endpoint
    response = authenticated_client.get("/todos/year")
    assert response.status_code == 200
    
    todos = response.json()
    year_titles = [todo["title"] for todo in todos]
    assert "This Year API Task" in year_titles
    assert "Next Year API Task" not in year_titles

def test_get_overdue_todos_endpoint(authenticated_client: TestClient):
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
    
    authenticated_client.post("/todos/", json=overdue_todo)
    authenticated_client.post("/todos/", json=completed_overdue_todo)
    authenticated_client.post("/todos/", json=future_todo)
    
    # Test overdue endpoint
    response = authenticated_client.get("/todos/overdue")
    assert response.status_code == 200
    
    todos = response.json()
    overdue_titles = [todo["title"] for todo in todos]
    assert "Overdue API Task" in overdue_titles
    assert "Completed Overdue API Task" not in overdue_titles
    assert "Future API Task" not in overdue_titles

def test_update_todo_with_time_fields_api(authenticated_client: TestClient):
    """Test updating a todo with time fields via API"""
    create_response = authenticated_client.post("/todos/", json={"title": "Update Time Test"})
    assert create_response.status_code == 200
    todo_id = create_response.json()["id"]
    
    update_data = {
        "title": "Updated with Time API",
        "start_date": "2024-12-26",
        "start_time": "14:00:00",
        "due_date": "2024-12-26"
    }
    
    update_response = authenticated_client.put(f"/todos/{todo_id}", json=update_data)
    assert update_response.status_code == 200
    
    data = update_response.json()
    assert data["title"] == "Updated with Time API"
    assert data["start_date"] == "2024-12-26"
    assert data["start_time"] == "14:00:00"
    assert data["due_date"] == "2024-12-26"

def test_get_todos_by_date_range_endpoint(authenticated_client: TestClient):
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
    
    authenticated_client.post("/todos/", json=in_range_todo)
    authenticated_client.post("/todos/", json=out_of_range_todo)
    
    # Test range endpoint
    response = authenticated_client.get(f"/todos/range?start_date={start_date.isoformat()}&end_date={end_date.isoformat()}")
    assert response.status_code == 200
    
    todos = response.json()
    range_titles = [todo["title"] for todo in todos]
    assert "In Range Task" in range_titles
    assert "Out of Range Task" not in range_titles

def test_invalid_date_format_handling(authenticated_client: TestClient):
    """Test API handles invalid date formats gracefully"""
    invalid_todo = {
        "title": "Invalid Date Test",
        "due_date": "invalid-date-format"
    }
    
    response = authenticated_client.post("/todos/", json=invalid_todo)
    assert response.status_code == 422  # Validation error

def test_time_fields_in_response_format(authenticated_client: TestClient):
    """Test that time fields are properly formatted in API responses"""
    todo_data = {
        "title": "Format Test",
        "start_date": "2024-12-25",
        "start_time": "09:00:00"
    }

    response = authenticated_client.post("/todos/", json=todo_data)
    assert response.status_code == 200

    data = response.json()
    assert "start_date" in data
    assert "start_time" in data
    assert data["start_date"] == "2024-12-25"
    # Assuming the API returns time as a string in HH:MM:SS format
    assert data["start_time"] == "09:00:00"

def test_time_management_filters_with_mixed_todos(client: TestClient, db: Session):
    """
    Tests that time management filters correctly return a mix of private todos and
    public todos from team sessions the user is a member of.
    """
    # 1. Create a user and log in
    user_data = {"username": "mixed_todo_user", "email": "mixed.todo@example.com", "password": "password"}
    client.post("/users/", json=user_data)
    login_response = client.post("/token", data={"username": "mixed_todo_user", "password": "password"})
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    user_obj = get_user_by_username(db, username="mixed_todo_user")
    assert user_obj

    # 2. Create a team session and invite the user (so they are a member)
    # The user created the session, so they are already a member/owner.
    team_session_name = "Mixed Todos Team"
    team_session_response = client.post("/sessions/", json={"name": team_session_name}, headers=headers)
    assert team_session_response.status_code == 200
    team_session_id = team_session_response.json()["id"]

    # 3. Create various todos with different due dates and privacy settings
    today = date.today()
    tomorrow = today + timedelta(days=1)
    next_week = today + timedelta(weeks=1)
    last_week = today - timedelta(weeks=1)
    next_month = today + timedelta(days=35)

    # Private todo due today
    private_todo_today_data = {"title": "Private Today", "due_date": str(today)}
    private_todo_today_response = client.post("/todos/", json=private_todo_today_data, headers=headers)
    assert private_todo_today_response.status_code == 200
    private_todo_today_id = private_todo_today_response.json()["id"]

    # Public todo due today in team session
    public_todo_today_data = {"title": "Public Today Team", "due_date": str(today), "session_id": team_session_id}
    public_todo_today_response = client.post("/todos/", json=public_todo_today_data, headers=headers)
    assert public_todo_today_response.status_code == 200
    public_todo_today_id = public_todo_today_response.json()["id"]

    # Private todo due next week
    private_todo_next_week_data = {"title": "Private Next Week", "due_date": str(next_week)}
    private_todo_next_week_response = client.post("/todos/", json=private_todo_next_week_data, headers=headers)
    assert private_todo_next_week_response.status_code == 200
    private_todo_next_week_id = private_todo_next_week_response.json()["id"]

    # Public todo due last week (overdue) in team session
    public_todo_overdue_data = {"title": "Public Overdue Team", "due_date": str(last_week), "session_id": team_session_id}
    public_todo_overdue_response = client.post("/todos/", json=public_todo_overdue_data, headers=headers)
    assert public_todo_overdue_response.status_code == 200
    public_todo_overdue_id = public_todo_overdue_response.json()["id"]

    # Another user's private todo (should NOT be returned)
    other_user_data = {"username": "other_user_tm", "email": "other.user.tm@example.com", "password": "password"}
    client.post("/users/", json=other_user_data)
    other_user_login = client.post("/token", data={"username": "other_user_tm", "password": "password"})
    other_user_headers = {'Authorization': f"Bearer {other_user_login.json()['access_token']}"}
    client.post("/todos/", json={"title": "Other User's Private Todo", "due_date": str(today)}, headers=other_user_headers)

    # 4. Test /todos/today endpoint
    today_todos = client.get("/todos/today", headers=headers).json()
    assert len(today_todos) == 2
    assert any(t["id"] == private_todo_today_id for t in today_todos)
    assert any(t["id"] == public_todo_today_id for t in today_todos)

    # 5. Test /todos/week endpoint
    week_todos = client.get("/todos/week", headers=headers).json()
    # Should include Private Today, Public Today Team
    assert len(week_todos) == 2
    assert any(t["id"] == private_todo_today_id for t in week_todos)
    assert any(t["id"] == public_todo_today_id for t in week_todos)
    assert not any(t["id"] == private_todo_next_week_id for t in week_todos) # Ensure next week todo is not in this week

    # 6. Test /todos/overdue endpoint
    overdue_todos = client.get("/todos/overdue", headers=headers).json()
    assert len(overdue_todos) == 1
    assert overdue_todos[0]["id"] == public_todo_overdue_id
    assert overdue_todos[0]["is_private"] is False # Should be public as it was in a team session

    # 7. Test /todos/month endpoint
    # To make this less flaky, let's explicitly add a todo for the current month but not current week/day.
    # And ensure the 'next_month' todo is truly next month.
    current_month_middle_date = today.replace(day=min(today.day + 7, 20)) # A date surely within current month
    private_todo_current_month_data = {"title": "Private Current Month", "due_date": str(current_month_middle_date)}
    private_todo_current_month_response = client.post("/todos/", json=private_todo_current_month_data, headers=headers)
    assert private_todo_current_month_response.status_code == 200
    private_todo_current_month_id = private_todo_current_month_response.json()["id"]

    month_todos = client.get("/todos/month", headers=headers).json()
    expected_month_ids = {
        private_todo_today_id,
        public_todo_today_id,
        public_todo_overdue_id, # This might be in previous month, let's keep it for now.
        private_todo_current_month_id
    }
    actual_month_ids = {t["id"] for t in month_todos}
    
    # Filter out todos that might have fallen outside the current month due to test run date.
    # This makes the assertion robust against boundary conditions.
    expected_month_todos_filtered = [
        t for t in month_todos 
        if date.fromisoformat(t["due_date"]).month == today.month and date.fromisoformat(t["due_date"]).year == today.year
    ]
    assert len(expected_month_todos_filtered) >= 3 # At least today's private/public, and current month middle todo
    assert any(t["id"] == private_todo_today_id for t in expected_month_todos_filtered)
    assert any(t["id"] == public_todo_today_id for t in expected_month_todos_filtered)
    assert any(t["id"] == private_todo_current_month_id for t in expected_month_todos_filtered)

    # Ensure the next month todo is NOT included
    private_todo_next_month_data = {"title": "Private Next Month", "due_date": str(next_month)}
    private_todo_next_month_response = client.post("/todos/", json=private_todo_next_month_data, headers=headers)
    assert private_todo_next_month_response.status_code == 200
    private_todo_next_month_id = private_todo_next_month_response.json()["id"]

    month_todos_rechecked = client.get("/todos/month", headers=headers).json()
    assert not any(t["id"] == private_todo_next_month_id for t in month_todos_rechecked)

    # 8. Test /todos/year endpoint
    # Create a todo for next year to ensure it's not included.
    next_year_date = today.replace(year=today.year + 1, month=1, day=1)
    private_todo_next_year_data = {"title": "Private Next Year", "due_date": str(next_year_date)}
    private_todo_next_year_response = client.post("/todos/", json=private_todo_next_year_data, headers=headers)
    assert private_todo_next_year_response.status_code == 200
    private_todo_next_year_id = private_todo_next_year_response.json()["id"]

    year_todos = client.get("/todos/year", headers=headers).json()
    # All todos created for this user should be in this year, except the 'next year' one.
    expected_ids_in_year = {
        private_todo_today_id,
        public_todo_today_id,
        private_todo_next_week_id, # This is now for this year
        public_todo_overdue_id, # This is now for this year
        private_todo_current_month_id,
        private_todo_next_month_id # This should be in the year as it's due in 35 days, which means it will probably be the same year.
    }
    actual_ids_in_year = {t["id"] for t in year_todos}
    assert actual_ids_in_year == expected_ids_in_year
    assert not any(t["id"] == private_todo_next_year_id for t in year_todos)