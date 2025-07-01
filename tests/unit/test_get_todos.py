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
    # Create a user and some todos
    user_in = schemas.UserCreate(username="testuser", password="testpassword")
    db_user = crud.create_user(db=db, user=user_in)
    
    crud.create_todo(db=db, todo=schemas.TodoCreate(title="Todo 1", due_date=datetime.utcnow().date()), owner_id=db_user.id)
    crud.create_todo(db=db, todo=schemas.TodoCreate(title="Todo 2", due_date=datetime.utcnow().date()), owner_id=db_user.id)

    # Retrieve the todos for the user
    todos = crud.get_todos_by_user(db=db, user_id=db_user.id)
    assert len(todos) == 2
    assert todos[0].title == "Todo 1"
    assert todos[1].title == "Todo 2"

def test_get_todos_data_isolation(db: Session):
    # Create user 1 and a todo
    user1_in = schemas.UserCreate(username="user1", password="pw1")
    db_user1 = crud.create_user(db=db, user=user1_in)
    crud.create_todo(db=db, todo=schemas.TodoCreate(title="User1 Todo"), owner_id=db_user1.id)

    # Create user 2 and a todo
    user2_in = schemas.UserCreate(username="user2", password="pw2")
    db_user2 = crud.create_user(db=db, user=user2_in)
    crud.create_todo(db=db, todo=schemas.TodoCreate(title="User2 Todo"), owner_id=db_user2.id)
    
    # Check that user 1 only sees their todo
    user1_todos = crud.get_todos_by_user(db=db, user_id=db_user1.id)
    assert len(user1_todos) == 1
    assert user1_todos[0].title == "User1 Todo"
    
    # Check that user 2 only sees their todo
    user2_todos = crud.get_todos_by_user(db=db, user_id=db_user2.id)
    assert len(user2_todos) == 1
    assert user2_todos[0].title == "User2 Todo" 