import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.crud import create_todo, update_todo
from app.models import Base
from app.schemas import ToDoCreate, ToDoUpdate

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

def test_update_todo(db_session: Session):
    todo_in = ToDoCreate(title="Initial Title", description="Initial description")
    db_todo = create_todo(db_session, todo_in)
    
    update_data = ToDoUpdate(title="Updated Title", done=True)
    updated_todo = update_todo(db_session, db_todo.id, update_data)
    
    assert updated_todo
    assert updated_todo.id == db_todo.id
    assert updated_todo.title == "Updated Title"
    assert updated_todo.description == "Initial description" # Description should not be updated
    assert updated_todo.done is True 