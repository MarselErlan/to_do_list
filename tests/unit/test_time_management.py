import pytest
from datetime import datetime, date, timedelta, time
from sqlalchemy.orm import Session
from app import crud, schemas
from app.models import Todo as TodoModel

def test_create_todo_with_time_fields(db: Session):
    """Test creating a todo with start_time, end_time, and due_date"""
    user_in = schemas.UserCreate(username="testuser", password="testpassword")
    db_user = crud.create_user(db=db, user=user_in)
    todo_data = schemas.TodoCreate(
        title="Time Management Test",
        description="Test with time fields",
        start_date=date(2024, 12, 25),
        start_time=datetime.strptime("09:00:00", "%H:%M:%S").time(),
        end_date=date(2024, 12, 25),
        end_time=datetime.strptime("10:30:00", "%H:%M:%S").time(),
        due_date=date(2024, 12, 25)
    )
    db_todo = crud.create_todo(db=db, todo=todo_data, owner_id=db_user.id)
    assert db_todo.start_date == todo_data.start_date
    assert db_todo.owner_id == db_user.id

def test_create_todo_without_time_fields(db: Session):
    """Test creating a todo without time fields (backward compatibility)"""
    user_in = schemas.UserCreate(username="testuser", password="testpassword")
    db_user = crud.create_user(db=db, user=user_in)
    todo_data = schemas.TodoCreate(
        title="Simple Todo",
        description="No time fields"
    )
    db_todo = crud.create_todo(db=db, todo=todo_data, owner_id=db_user.id)
    assert db_todo.title == todo_data.title
    assert db_todo.owner_id == db_user.id

def test_get_todos_for_today(db: Session):
    """Test filtering todos for today"""
    user_in = schemas.UserCreate(username="testuser", password="testpassword")
    db_user = crud.create_user(db=db, user=user_in)
    today = date.today()
    todo_today = schemas.TodoCreate(
        title="Today's Task",
        due_date=today
    )
    crud.create_todo(db=db, todo=todo_today, owner_id=db_user.id)
    todos = crud.get_todos_today(db=db, user_id=db_user.id)
    assert len(todos) == 1
    assert todos[0].title == "Today's Task"

def test_get_todos_for_week(db: Session):
    """Test filtering todos for this week"""
    user_in = schemas.UserCreate(username="testuser", password="testpassword")
    db_user = crud.create_user(db=db, user=user_in)
    today = date.today()
    days_since_monday = today.weekday()
    week_start = today - timedelta(days=days_since_monday)

    todo_this_week = schemas.TodoCreate(
        title="This Week Task",
        due_date=week_start + timedelta(days=2)
    )
    crud.create_todo(db=db, todo=todo_this_week, owner_id=db_user.id)
    todos = crud.get_todos_for_week(db=db, user_id=db_user.id)
    assert len(todos) == 1
    assert todos[0].title == "This Week Task"

def test_get_todos_for_month(db: Session):
    """Test filtering todos for this month"""
    user_in = schemas.UserCreate(username="testuser", password="testpassword")
    db_user = crud.create_user(db=db, user=user_in)
    today = date.today()
    
    todo_this_month = schemas.TodoCreate(
        title="This Month Task",
        due_date=today.replace(day=15)
    )
    crud.create_todo(db=db, todo=todo_this_month, owner_id=db_user.id)
    todos = crud.get_todos_for_month(db=db, user_id=db_user.id)
    assert len(todos) >= 1 # Can be more than 1 if other tests run in same month
    assert any(t.title == "This Month Task" for t in todos)

def test_get_todos_for_year(db: Session):
    """Test filtering todos for this year"""
    user_in = schemas.UserCreate(username="testuser", password="testpassword")
    db_user = crud.create_user(db=db, user=user_in)
    today = date.today()

    todo_this_year = schemas.TodoCreate(
        title="This Year Task",
        due_date=today.replace(month=6, day=15)
    )
    crud.create_todo(db=db, todo=todo_this_year, owner_id=db_user.id)
    todos = crud.get_todos_for_year(db=db, user_id=db_user.id)
    assert len(todos) >= 1
    assert any(t.title == "This Year Task" for t in todos)

def test_get_overdue_todos(db: Session):
    """Test filtering overdue todos"""
    user_in = schemas.UserCreate(username="testuser", password="testpassword")
    db_user = crud.create_user(db=db, user=user_in)
    today = date.today()
    overdue_todo = schemas.TodoCreate(
        title="Overdue Task",
        due_date=today - timedelta(days=1),
        done=False
    )
    crud.create_todo(db=db, todo=overdue_todo, owner_id=db_user.id)
    todos = crud.get_overdue_todos(db=db, user_id=db_user.id)
    assert len(todos) == 1
    assert todos[0].title == "Overdue Task"

def test_update_todo_with_time_fields(db: Session):
    """Test updating a todo with time fields"""
    user_in = schemas.UserCreate(username="testuser", password="testpassword")
    db_user = crud.create_user(db=db, user=user_in)
    todo_data = schemas.TodoCreate(
        title="Update Test",
        description="Initial description"
    )
    db_todo = crud.create_todo(db=db, todo=todo_data, owner_id=db_user.id)
    
    update_data = schemas.TodoUpdate(
        start_date=date(2025, 1, 1),
        start_time=time(14, 30)
    )
    updated_todo = crud.update_todo(db=db, todo_id=db_todo.id, todo=update_data, owner_id=db_user.id)
    assert updated_todo.start_date == date(2025, 1, 1)
    assert updated_todo.start_time == time(14, 30)

def test_get_todos_with_time_range(db: Session):
    """Test filtering todos by time range"""
    user_in = schemas.UserCreate(username="testuser", password="testpassword")
    db_user = crud.create_user(db=db, user=user_in)
    today = date.today()
    morning_todo = schemas.TodoCreate(
        title="Morning Task",
        start_time=datetime.strptime("09:00", "%H:%M").time(),
        due_date=today
    )
    crud.create_todo(db=db, todo=morning_todo, owner_id=db_user.id)
    
    evening_todo = schemas.TodoCreate(
        title="Evening Task",
        start_time=datetime.strptime("20:00", "%H:%M").time(),
        due_date=today
    )
    crud.create_todo(db=db, todo=evening_todo, owner_id=db_user.id)
    
    start_of_day = datetime.combine(today, time.min)
    end_of_day = datetime.combine(today, time.max)
    
    todos = crud.get_todos_by_date_range(db, user_id=db_user.id, start_date=start_of_day.date(), end_date=end_of_day.date())
    assert len(todos) == 2 