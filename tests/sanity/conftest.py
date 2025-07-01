import pytest
import requests
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
import os
import sys

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
def test_db():
    """Create and teardown test database for each test"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(test_db):
    """Create a test client with clean database"""
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture(scope="session")
def live_api_url():
    """URL for live API testing (Railway deployment)"""
    # You can override this with environment variable
    return os.getenv("LIVE_API_URL", "https://your-railway-url.up.railway.app")

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