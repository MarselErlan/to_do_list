import pytest
import requests
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
import os
import sys
from sqlalchemy.orm import Session

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app.main import app, get_db
from app.database import Base
from app import models

# Test database URL
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_sanity.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

@pytest.fixture(scope="function")
def db():
    """Create and teardown test database for each test function."""
    Base.metadata.create_all(bind=engine)
    db_session = TestingSessionLocal()
    try:
        yield db_session
    finally:
        db_session.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db):
    """Create a test client with a clean database for each function."""
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture(scope="session")
def live_api_url():
    """URL for live API testing (Railway deployment)"""
    # You can override this with environment variable
    return os.getenv("LIVE_API_URL", "https://web-production-56fee.up.railway.app")

@pytest.fixture(scope="session")
def live_frontend_url():
    """URL for live frontend testing"""
    return "https://marsel-to-do-list.vercel.app"

@pytest.fixture
def sample_todo():
    """Sample todo data for testing"""
    return {
        "title": "Sanity Test Todo",
        "description": "This is a sanity test todo item",
        "done": False
    }

@pytest.fixture(scope="function")
def authenticated_headers(client: TestClient, db: Session) -> dict:
    """
    Creates a new user and returns authentication headers for them.
    """
    from app import crud, schemas
    import uuid

    # Use a unique username for each test function to ensure isolation
    username = f"testuser_{uuid.uuid4().hex}"
    password = "testpassword"

    user_data = schemas.UserCreate(
        username=username,
        email=f"{username}@example.com",
        password=password
    )
    crud.create_user(db=db, user=user_data)
    db.commit()

    # Log in to get token
    response = client.post(
        "/token",
        data={"username": username, "password": password}
    )
    assert response.status_code == 200, "Failed to log in and get token"
    token = response.json()["access_token"]

    return {"Authorization": f"Bearer {token}"} 