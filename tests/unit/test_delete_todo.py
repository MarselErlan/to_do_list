import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app import crud, schemas
from app.models import Base
from datetime import datetime

# Use an in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    """
    Create a new database session for each test.
    """
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

def test_delete_todo(db: Session):
    # First, create a user and a todo to delete
    user_in = schemas.UserCreate(username="testuser", password="testpassword")
    db_user = crud.create_user(db=db, user=user_in)
    todo_in = schemas.TodoCreate(
        title="Delete Me",
        description="A todo to be deleted",
        due_date=datetime.utcnow().date()
    )
    db_todo = crud.create_todo(db=db, todo=todo_in, owner_id=db_user.id)
    
    # Delete the todo
    deleted_todo = crud.delete_todo(db=db, todo_id=db_todo.id)
    assert deleted_todo.id == db_todo.id
    
    # Verify it's gone
    assert crud.get_todo(db=db, todo_id=db_todo.id) is None
    
    # Verify it's not in the user's list of todos
    todos = crud.get_todos_by_user(db=db, user_id=db_user.id)
    assert db_todo not in todos 