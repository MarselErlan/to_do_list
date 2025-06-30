from sqlalchemy.orm import Session
from app import crud, schemas

def test_get_non_existent_todo(db: Session):
    """
    Test that fetching a non-existent to-do returns None.
    """
    todo = crud.get_todo(db, todo_id=999)
    assert todo is None

def test_update_non_existent_todo(db: Session):
    """
    Test that updating a non-existent to-do returns None.
    """
    update_data = schemas.ToDoUpdate(title="I should not exist")
    todo = crud.update_todo(db, todo_id=999, todo=update_data)
    assert todo is None

def test_delete_non_existent_todo(db: Session):
    """
    Test that deleting a non-existent to-do returns None.
    """
    todo = crud.delete_todo(db, todo_id=999)
    assert todo is None 