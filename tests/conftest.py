import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import os

from app.main import app, get_db
from app.database import Base

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

@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=engine)
    db_session = TestingSessionLocal()
    try:
        yield db_session
    finally:
        db_session.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db):
    def override_get_db():
        yield db
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()

@pytest.fixture(scope="function")
def authenticated_client(client: TestClient, db):
    from app.schemas import UserCreate
    from app.crud import create_user
    # Create a test user
    user_data = UserCreate(email="test@example.com", username="testuser", password="password")
    user = create_user(db, user_data)
    
    # Log in to get the token
    login_data = {"username": "testuser", "password": "password"}
    response = client.post("/token", data=login_data)
    token = response.json()["access_token"]
    
    # Set the authorization header
    client.headers["Authorization"] = f"Bearer {token}"
    
    return client 