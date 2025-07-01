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
    # First, create a todo
    todo_in = schemas.TodoCreate(
        title="Original Title", 
        description="Original Description",
        due_date=datetime.utcnow().date()
    )
    db_todo = crud.create_todo(db=db, todo=todo_in)
    todo_id = db_todo.id

    # Now, update it
    update_data = schemas.TodoUpdate(title="Updated Title", done=True)
    updated_todo = crud.update_todo(db=db, todo_id=todo_id, todo=update_data)
    
    assert updated_todo.title == "Updated Title"
    assert updated_todo.done is True
    assert updated_todo.description == "Original Description" # Should not change 