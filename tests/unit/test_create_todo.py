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

def test_create_todo(db: Session):
    todo_in = schemas.TodoCreate(
        title="Test Todo", 
        description="Test Description",
        due_date=datetime.utcnow().date()
    )
    db_todo = crud.create_todo(db=db, todo=todo_in)
    assert db_todo.title == todo_in.title
    assert db_todo.description == todo_in.description
    assert db_todo.due_date == todo_in.due_date
    assert db_todo.id is not None 