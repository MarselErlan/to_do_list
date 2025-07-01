import pytest
from sqlalchemy.orm import Session
from app import crud, schemas

def test_get_non_existent_todo(db: Session):
    """
    Test that retrieving a non-existent to-do returns None.
    """
    retrieved_todo = crud.get_todo(db=db, todo_id=99999)
    assert retrieved_todo is None

def test_update_non_existent_todo(db: Session):
    """
    Test that updating a non-existent to-do returns None.
    """
    update_data = schemas.TodoUpdate(title="I should not exist")
    updated_todo = crud.update_todo(db=db, todo_id=99999, todo=update_data)
    assert updated_todo is None

def test_delete_non_existent_todo(db: Session):
    """
    Test that deleting a non-existent to-do returns None.
    """
    deleted_todo = crud.delete_todo(db=db, todo_id=99999)
    assert deleted_todo is None 