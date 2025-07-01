from sqlalchemy.orm import Session
from app.models import Todo
from datetime import datetime

def test_todo_model_defaults(db: Session):
    """
    Tests that the database schema correctly applies the default value for the 'done' field.
    """
    # 1. Arrange: Create a new ToDo object with only the required field
    # We are intentionally NOT setting the 'done' attribute.
    new_todo = Todo(title="Test Default Value")

    # 2. Act: Add it to the database and commit
    db.add(new_todo)
    db.commit()
    db.refresh(new_todo) # Load the full object from the DB, including defaults

    # 3. Assert: Verify that the 'done' field was defaulted to False by the database
    assert new_todo.done is False
    assert new_todo.title == "Test Default Value"
    assert new_todo.id is not None

def test_todo_model():
    todo = Todo(
        title="Test Model",
        description="A test for the model",
        done=False,
        due_date=datetime.utcnow().date()
    )
    assert todo.title == "Test Model"
    assert todo.done is False
    assert todo.due_date is not None 