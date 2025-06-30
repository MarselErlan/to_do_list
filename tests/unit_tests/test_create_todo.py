import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.crud import create_todo
from app.models import Base
from app.schemas import ToDoCreate

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

def test_create_todo(db_session: Session):
    todo_in = ToDoCreate(title="Test Todo", description="Test description")
    db_todo = create_todo(db_session, todo_in)
    assert db_todo.id is not None
    assert db_todo.title == "Test Todo"
    assert db_todo.description == "Test description"
    assert not db_todo.done 