import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
import sys
import os

# Set environment variables for testing before app import
os.environ["SECRET_KEY"] = "super-secret-test-key"
os.environ["MAIL_USERNAME"] = "test@example.com"
os.environ["MAIL_PASSWORD"] = "testpassword"
os.environ["MAIL_FROM"] = "test@example.com"
os.environ["MAIL_PORT"] = "587"
os.environ["MAIL_SERVER"] = "smtp.test.com"
os.environ["MAIL_STARTTLS"] = "True"
os.environ["MAIL_SSL_TLS"] = "False"
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["SUPPRESS_SEND"] = "True" # Ensure emails are suppressed during testing
os.environ["ALGORITHM"] = "HS256"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "30"
os.environ["OPENAI_API_KEY"] = "test-key"

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.main import app, get_db
from app.database import Base
from app import models


SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session")
def live_api_url():
    """Get the live API URL from environment or use default Railway URL"""
    return os.getenv("LIVE_API_URL", "https://web-production-56fee.up.railway.app/")

@pytest.fixture(scope="session")
def frontend_url():
    """Get the frontend URL from environment or use default Vercel URL"""
    return os.getenv("FRONTEND_URL", "https://marsel-to-do-list.vercel.app")

@pytest.fixture(scope="session")
def test_db():
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def db(test_db):
    connection = test_db.connect()
    transaction = connection.begin()
    db_session = Session(bind=connection)
    try:
        yield db_session
    finally:
        db_session.close()
        transaction.rollback()
        connection.close()

@pytest.fixture()
def client(db):
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    del app.dependency_overrides[get_db]

@pytest.fixture()
def authenticated_client(client: TestClient, db: Session):
    """
    Creates a user, logs them in, and returns an authenticated client.
    """
    from app.schemas import UserCreate
    from app.crud import create_user

    # Create a test user
    user_data = UserCreate(email="test@example.com", username="testuser", password="password")
    create_user(db, user_data)
    
    # Log in to get the token
    login_data = {"username": "testuser", "password": "password"}
    response = client.post("/token", data=login_data)
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    
    # Set the authorization header
    client.headers["Authorization"] = f"Bearer {token}"
    
    return client 

@pytest.fixture
def test_user_token_headers(client: TestClient, db: Session) -> dict:
    """
    Creates a dedicated user for a test and returns their auth token headers.
    """
    from app.schemas import UserCreate
    from app.crud import create_user
    
    test_username = "test_user_for_headers"
    test_password = "password"
    user_data = UserCreate(username=test_username, password=test_password, email=f"{test_username}@example.com")
    
    # Ensure the user exists for the test
    existing_user = db.query(models.User).filter_by(username=test_username).first()
    if not existing_user:
        create_user(db=db, user=user_data)

    # Log in to get the token
    response = client.post("/token", data={"username": test_username, "password": test_password})
    assert response.status_code == 200, "Failed to log in for headers"
    token = response.json().get("access_token")
    
    return {"Authorization": f"Bearer {token}"} 