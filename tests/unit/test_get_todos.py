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

def test_get_todos(db: Session):
    # Create a couple of todos
    crud.create_todo(db=db, todo=schemas.TodoCreate(title="Todo 1", due_date=datetime.utcnow().date()))
    crud.create_todo(db=db, todo=schemas.TodoCreate(title="Todo 2", due_date=datetime.utcnow().date()))

    # Retrieve them
    todos_list = crud.get_todos(db=db)
    assert len(todos_list) >= 2 