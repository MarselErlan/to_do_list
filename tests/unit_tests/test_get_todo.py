import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.crud import create_todo, get_todo
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

def test_get_todo(db_session: Session):
    todo_in = ToDoCreate(title="Test Get Todo", description="Test get description")
    db_todo = create_todo(db_session, todo_in)
    retrieved_todo = get_todo(db_session, db_todo.id)
    assert retrieved_todo
    assert retrieved_todo.id == db_todo.id
    assert retrieved_todo.title == "Test Get Todo" 