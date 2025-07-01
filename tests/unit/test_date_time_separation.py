import pytest
from sqlalchemy.orm import Session
from app import crud, schemas
from datetime import date, time

def test_create_todo_with_separate_date_time(db: Session):
    """
    Test creating a todo with separate date and time fields.
    """
    todo_in = schemas.TodoCreate(
        title="Test TDD Todo",
        description="A todo for testing TDD",
        start_date=date(2025, 1, 1),
        start_time=time(9, 0, 0),
        end_date=date(2025, 1, 1),
        end_time=time(17, 0, 0),
        due_date=date(2025, 1, 5)
    )
    db_todo = crud.create_todo(db=db, todo=todo_in)
    assert db_todo.title == todo_in.title
    assert db_todo.description == todo_in.description
    assert db_todo.start_date == todo_in.start_date
    assert db_todo.start_time == todo_in.start_time
    assert db_todo.end_date == todo_in.end_date
    assert db_todo.end_time == todo_in.end_time
    assert db_todo.due_date == todo_in.due_date
    assert db_todo.id is not None 