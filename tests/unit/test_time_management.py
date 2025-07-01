import pytest
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from app import crud, schemas

def test_create_todo_with_time_fields(db: Session):
    """Test creating a todo with start_time, end_time, and due_date"""
    todo_data = schemas.TodoCreate(
        title="Time Management Test",
        description="Test with time fields",
        start_date=date(2024, 12, 25),
        start_time=datetime.strptime("09:00:00", "%H:%M:%S").time(),
        end_date=date(2024, 12, 25),
        end_time=datetime.strptime("10:30:00", "%H:%M:%S").time(),
        due_date=date(2024, 12, 25)
    )
    db_todo = crud.create_todo(db=db, todo=todo_data)
    assert db_todo.start_date == date(2024, 12, 25)
    assert db_todo.start_time.strftime("%H:%M:%S") == "09:00:00"
    assert db_todo.due_date == date(2024, 12, 25)

def test_create_todo_without_time_fields(db: Session):
    """Test creating a todo without time fields (backward compatibility)"""
    todo_data = schemas.TodoCreate(
        title="Simple Todo",
        description="No time fields"
    )
    db_todo = crud.create_todo(db=db, todo=todo_data)
    assert db_todo.title == "Simple Todo"
    assert db_todo.start_date is None

def test_get_todos_for_today(db: Session):
    """Test filtering todos for today"""
    today = date.today()
    todo_today = schemas.TodoCreate(
        title="Today's Task",
        due_date=today
    )
    crud.create_todo(db=db, todo=todo_today)
    
    todos_for_today = crud.get_todos_by_date(db, target_date=today)
    assert len(todos_for_today) >= 1
    assert all(todo.due_date == today for todo in todos_for_today)

def test_get_todos_for_week(db: Session):
    """Test filtering todos for this week"""
    today = date.today()
    days_since_monday = today.weekday()
    week_start = today - timedelta(days=days_since_monday)
    
    todo_this_week = schemas.TodoCreate(
        title="This Week Task",
        due_date=week_start + timedelta(days=2)
    )
    crud.create_todo(db=db, todo=todo_this_week)
    
    todos_for_week = crud.get_todos_by_date_range(db, start_date=week_start, end_date=week_start + timedelta(days=6))
    assert any(t.title == "This Week Task" for t in todos_for_week)

def test_get_todos_for_month(db: Session):
    """Test filtering todos for this month"""
    today = date.today()
    month_start = today.replace(day=1)
    
    todo_this_month = schemas.TodoCreate(
        title="This Month Task",
        due_date=today.replace(day=15)
    )
    crud.create_todo(db=db, todo=todo_this_month)
    
    next_month = month_start.replace(month=month_start.month % 12 + 1)
    month_end = next_month - timedelta(days=1)
    
    todos_for_month = crud.get_todos_by_date_range(db, start_date=month_start, end_date=month_end)
    assert any(t.title == "This Month Task" for t in todos_for_month)

def test_get_todos_for_year(db: Session):
    """Test filtering todos for this year"""
    today = date.today()
    year_start = today.replace(day=1, month=1)
    
    todo_this_year = schemas.TodoCreate(
        title="This Year Task",
        due_date=today.replace(month=6, day=15)
    )
    crud.create_todo(db=db, todo=todo_this_year)
    
    todos_for_year = crud.get_todos_by_date_range(db, start_date=year_start, end_date=today.replace(day=31, month=12))
    assert any(t.title == "This Year Task" for t in todos_for_year)

def test_get_overdue_todos(db: Session):
    """Test filtering overdue todos"""
    today = date.today()
    overdue_todo = schemas.TodoCreate(
        title="Overdue Task",
        due_date=today - timedelta(days=1),
        done=False
    )
    crud.create_todo(db=db, todo=overdue_todo)
    
    overdue_list = crud.get_overdue_todos(db)
    assert any(t.title == "Overdue Task" for t in overdue_list)

def test_update_todo_with_time_fields(db: Session):
    """Test updating a todo with time fields"""
    todo_data = schemas.TodoCreate(
        title="Update Test",
        description="Initial description"
    )
    db_todo = crud.create_todo(db=db, todo=todo_data)
    
    update_data = schemas.TodoUpdate(
        start_date=date(2024, 1, 1),
        end_time=datetime.strptime("14:00", "%H:%M").time()
    )
    updated_todo = crud.update_todo(db=db, todo_id=db_todo.id, todo=update_data)
    assert updated_todo.start_date == date(2024, 1, 1)

def test_get_todos_with_time_range(db: Session):
    """Test filtering todos by time range"""
    today = date.today()
    morning_todo = schemas.TodoCreate(
        title="Morning Task",
        start_time=datetime.strptime("09:00", "%H:%M").time(),
        due_date=today
    )
    crud.create_todo(db=db, todo=morning_todo)
    
    todos_in_range = crud.get_todos_by_date_range(db, start_date=today, end_date=today)
    assert any(t.title == "Morning Task" for t in todos_in_range) 