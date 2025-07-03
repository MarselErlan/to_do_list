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

def test_update_todo(db: Session):
    # First, create a user and a todo
    user_in = schemas.UserCreate(username="testuser", password="testpassword")
    db_user = crud.create_user(db=db, user=user_in)
    todo_in = schemas.TodoCreate(
        title="Original Title",
        description="Original Description",
        due_date=datetime.utcnow().date()
    )
    db_todo = crud.create_todo(db=db, todo=todo_in, owner_id=db_user.id)
    
    # Now, update it
    update_data = schemas.TodoUpdate(title="Updated Title", done=True)
    updated_todo = crud.update_todo(db=db, todo_id=db_todo.id, todo=update_data, owner_id=db_user.id)
    
    assert updated_todo is not None
    assert updated_todo.title == "Updated Title"
    assert updated_todo.done is True
    assert updated_todo.id == db_todo.id
    assert updated_todo.owner_id == db_user.id
    assert updated_todo.description == "Original Description" 