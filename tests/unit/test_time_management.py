import pytest
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from app import crud, schemas

def test_create_todo_with_time_fields(db: Session):
    """Test creating a todo with start_time, end_time, and due_date"""
    start_time = datetime(2024, 12, 25, 9, 0)  # 9:00 AM
    end_time = datetime(2024, 12, 25, 10, 30)  # 10:30 AM
    due_date = date(2024, 12, 25)
    
    todo_data = schemas.ToDoCreate(
        title="Time Management Test",
        description="Test with time fields",
        start_time=start_time,
        end_time=end_time,
        due_date=due_date
    )
    
    created_todo = crud.create_todo(db, todo_data)
    
    assert created_todo.title == "Time Management Test"
    assert created_todo.start_time == start_time
    assert created_todo.end_time == end_time
    assert created_todo.due_date == due_date
    assert created_todo.done == False

def test_create_todo_without_time_fields(db: Session):
    """Test creating a todo without time fields (backward compatibility)"""
    todo_data = schemas.ToDoCreate(
        title="Simple Todo",
        description="No time fields"
    )
    
    created_todo = crud.create_todo(db, todo_data)
    
    assert created_todo.title == "Simple Todo"
    assert created_todo.start_time is None
    assert created_todo.end_time is None
    assert created_todo.due_date is None

def test_get_todos_for_today(db: Session):
    """Test filtering todos for today"""
    today = date.today()
    tomorrow = today + timedelta(days=1)
    yesterday = today - timedelta(days=1)
    
    # Create todos with different due dates
    todo_today = schemas.ToDoCreate(
        title="Today's Task",
        due_date=today
    )
    todo_tomorrow = schemas.ToDoCreate(
        title="Tomorrow's Task", 
        due_date=tomorrow
    )
    todo_yesterday = schemas.ToDoCreate(
        title="Yesterday's Task",
        due_date=yesterday
    )
    
    crud.create_todo(db, todo_today)
    crud.create_todo(db, todo_tomorrow)
    crud.create_todo(db, todo_yesterday)
    
    # Get today's todos
    today_todos = crud.get_todos_for_today(db)
    
    assert len(today_todos) == 1
    assert today_todos[0].title == "Today's Task"
    assert today_todos[0].due_date == today

def test_get_todos_for_week(db: Session):
    """Test filtering todos for this week"""
    today = date.today()
    
    # Calculate week boundaries
    days_since_monday = today.weekday()
    week_start = today - timedelta(days=days_since_monday)
    week_end = week_start + timedelta(days=6)
    
    # Create todos
    todo_this_week = schemas.ToDoCreate(
        title="This Week Task",
        due_date=week_start + timedelta(days=2)  # Wednesday
    )
    todo_next_week = schemas.ToDoCreate(
        title="Next Week Task",
        due_date=week_end + timedelta(days=2)  # Next Tuesday
    )
    
    crud.create_todo(db, todo_this_week)
    crud.create_todo(db, todo_next_week)
    
    # Get this week's todos
    week_todos = crud.get_todos_for_week(db)
    
    assert len(week_todos) == 1
    assert week_todos[0].title == "This Week Task"

def test_get_todos_for_month(db: Session):
    """Test filtering todos for this month"""
    today = date.today()
    
    # Create todos
    todo_this_month = schemas.ToDoCreate(
        title="This Month Task",
        due_date=today.replace(day=15)  # 15th of current month
    )
    todo_next_month = schemas.ToDoCreate(
        title="Next Month Task",
        due_date=(today.replace(day=28) + timedelta(days=4)).replace(day=15)  # Next month
    )
    
    crud.create_todo(db, todo_this_month)
    crud.create_todo(db, todo_next_month)
    
    # Get this month's todos
    month_todos = crud.get_todos_for_month(db)
    
    assert len(month_todos) == 1
    assert month_todos[0].title == "This Month Task"

def test_get_todos_for_year(db: Session):
    """Test filtering todos for this year"""
    today = date.today()
    
    # Create todos
    todo_this_year = schemas.ToDoCreate(
        title="This Year Task",
        due_date=today.replace(month=6, day=15)  # June 15th this year
    )
    todo_next_year = schemas.ToDoCreate(
        title="Next Year Task",
        due_date=today.replace(year=today.year + 1, month=1, day=15)  # Next year
    )
    
    crud.create_todo(db, todo_this_year)
    crud.create_todo(db, todo_next_year)
    
    # Get this year's todos
    year_todos = crud.get_todos_for_year(db)
    
    assert len(year_todos) == 1
    assert year_todos[0].title == "This Year Task"

def test_get_overdue_todos(db: Session):
    """Test filtering overdue todos"""
    today = date.today()
    yesterday = today - timedelta(days=1)
    tomorrow = today + timedelta(days=1)
    
    # Create todos
    overdue_todo = schemas.ToDoCreate(
        title="Overdue Task",
        due_date=yesterday,
        done=False
    )
    completed_overdue = schemas.ToDoCreate(
        title="Completed Overdue Task",
        due_date=yesterday,
        done=True
    )
    future_todo = schemas.ToDoCreate(
        title="Future Task",
        due_date=tomorrow,
        done=False
    )
    
    crud.create_todo(db, overdue_todo)
    crud.create_todo(db, completed_overdue)
    crud.create_todo(db, future_todo)
    
    # Get overdue todos
    overdue_todos = crud.get_overdue_todos(db)
    
    assert len(overdue_todos) == 1
    assert overdue_todos[0].title == "Overdue Task"
    assert overdue_todos[0].done == False

def test_update_todo_with_time_fields(db: Session):
    """Test updating a todo with time fields"""
    # Create initial todo
    todo_data = schemas.ToDoCreate(
        title="Update Test",
        description="Initial description"
    )
    created_todo = crud.create_todo(db, todo_data)
    
    # Update with time fields
    new_start_time = datetime(2024, 12, 26, 14, 0)  # 2:00 PM
    new_end_time = datetime(2024, 12, 26, 15, 30)   # 3:30 PM
    new_due_date = date(2024, 12, 26)
    
    update_data = schemas.ToDoUpdate(
        title="Updated with Time",
        start_time=new_start_time,
        end_time=new_end_time,
        due_date=new_due_date
    )
    
    updated_todo = crud.update_todo(db, created_todo.id, update_data)
    
    assert updated_todo.title == "Updated with Time"
    assert updated_todo.start_time == new_start_time
    assert updated_todo.end_time == new_end_time
    assert updated_todo.due_date == new_due_date

def test_get_todos_with_time_range(db: Session):
    """Test filtering todos by time range"""
    today = date.today()
    
    # Create todos with start times
    morning_todo = schemas.ToDoCreate(
        title="Morning Task",
        start_time=datetime.combine(today, datetime.min.time().replace(hour=9)),
        due_date=today
    )
    evening_todo = schemas.ToDoCreate(
        title="Evening Task",
        start_time=datetime.combine(today, datetime.min.time().replace(hour=18)),
        due_date=today
    )
    
    crud.create_todo(db, morning_todo)
    crud.create_todo(db, evening_todo)
    
    # Get todos in morning time range (8 AM - 12 PM)
    morning_start = datetime.combine(today, datetime.min.time().replace(hour=8))
    morning_end = datetime.combine(today, datetime.min.time().replace(hour=12))
    
    morning_todos = crud.get_todos_by_time_range(db, morning_start, morning_end)
    
    assert len(morning_todos) == 1
    assert morning_todos[0].title == "Morning Task" 