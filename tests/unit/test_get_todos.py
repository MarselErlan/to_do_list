import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.crud import create_todo, get_todos
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

def test_get_todos(db_session: Session):
    todo1_in = ToDoCreate(title="Test Todo 1")
    todo2_in = ToDoCreate(title="Test Todo 2")
    create_todo(db_session, todo1_in)
    create_todo(db_session, todo2_in)
    
    todos = get_todos(db_session)
    assert len(todos) == 2
    assert todos[0].title == "Test Todo 1"
    assert todos[1].title == "Test Todo 2" 