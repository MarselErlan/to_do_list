import pytest
from sqlalchemy.orm import Session
from app import crud, schemas, models
from datetime import date, time

def test_create_todo_with_separate_date_time(db: Session):
    """
    Test creating a todo with separate date and time fields.
    """
    # Create a user first
    user_in = schemas.UserCreate(username="testuser", password="testpassword")
    db_user = crud.create_user(db=db, user=user_in)

    todo_in = schemas.TodoCreate(
        title="Test TDD Todo",
        description="A todo for testing TDD",
        start_date=date(2025, 1, 1),
        start_time=time(9, 0, 0),
        end_date=date(2025, 1, 1),
        end_time=time(17, 0, 0),
        due_date=date(2025, 1, 5)
    )
    db_todo = crud.create_todo(db=db, todo=todo_in, owner_id=db_user.id)
    assert db_todo.title == "Test TDD Todo"
    assert db_todo.start_date == date(2025, 1, 1)
    assert db_todo.start_time == time(9, 0, 0)
    assert db_todo.owner_id == db_user.id 