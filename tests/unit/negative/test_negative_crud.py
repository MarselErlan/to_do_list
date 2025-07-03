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
    # Create a dummy user, as owner_id is now required
    user_in = schemas.UserCreate(username="dummyuser_update_non_existent", password="testpassword")
    db_user = crud.create_user(db=db, user=user_in)

    update_data = schemas.TodoUpdate(title="I should not exist")
    updated_todo = crud.update_todo(db=db, todo_id=99999, todo=update_data, owner_id=db_user.id)
    assert updated_todo is None

def test_delete_non_existent_todo(db: Session):
    """
    Test that deleting a non-existent to-do returns None.
    """
    deleted_todo = crud.delete_todo(db=db, todo_id=99999)
    assert deleted_todo is None 