import pytest
import uuid
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import get_db, Base
from app import crud, schemas, models
from app.security import create_access_token
import os

# Use PostgreSQL for tests (same as production)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:OZNHVfQlRwGhcUBFmkVluOzTonqTpIKa@interchange.proxy.rlwy.net:30153/railway")
engine = create_engine(DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="session")
def setup_database():
    # Database is already set up in production, no need to create/drop tables
    yield

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def unique_test_user():
    """Create a unique test user for each test to avoid conflicts."""
    unique_id = str(uuid.uuid4())[:8]
    db = TestingSessionLocal()
    try:
        # Create test user with unique identifiers
        user_data = schemas.UserCreate(
            username=f"testuser_{unique_id}",
            email=f"test_{unique_id}@example.com",
            password="testpassword123"
        )
        user = crud.create_user(db=db, user=user_data)
        
        # Create access token
        access_token = create_access_token(data={"sub": user.username})
        return user, access_token
    finally:
        db.close()

def test_database_schema_has_privacy_fields(setup_database):
    """Test that the database schema includes is_private and is_global_public columns."""
    unique_id = str(uuid.uuid4())[:8]
    db = TestingSessionLocal()
    try:
        # Create a unique user for this test
        user_data = schemas.UserCreate(
            username=f"schematest_{unique_id}",
            email=f"schema_{unique_id}@example.com", 
            password="testpass123"
        )
        user = crud.create_user(db=db, user=user_data)
        
        # Create a todo directly via CRUD to test the database schema
        todo_data = schemas.TodoCreate(
            title="Schema Test Todo",
            description="Testing database schema",
            is_private=True,
            is_global_public=False
        )
        
        # This should succeed if the database schema is correct
        todo = crud.create_todo(db=db, todo=todo_data, owner_id=user.id)
        
        assert todo.title == "Schema Test Todo"
        assert todo.is_private is True
        assert todo.is_global_public is False
        
        # Verify we can query it back from the database
        db_todo = db.query(models.Todo).filter(models.Todo.id == todo.id).first()
        assert db_todo is not None
        assert db_todo.is_private is True
        assert db_todo.is_global_public is False
        
        # Note: We don't clean up from production database
        # The test data will remain but that's acceptable for schema validation
        
    finally:
        db.close()

def test_create_todo_with_privacy_fields(client, unique_test_user):
    """Test creating a todo with is_private and is_global_public fields via API."""
    user, token = unique_test_user
    headers = {"Authorization": f"Bearer {token}"}
    
    todo_payload = {
        "title": "Test Todo with Privacy Fields",
        "description": "Testing is_private and is_global_public fields",
        "is_private": True,
        "is_global_public": False
    }
    
    response = client.post("/todos/", headers=headers, json=todo_payload)
    
    # This test should pass now that the database migration is applied
    assert response.status_code == 200, f"Expected 200, got {response.status_code}. Response: {response.text}"
    
    data = response.json()
    assert data["title"] == todo_payload["title"]
    assert data["description"] == todo_payload["description"]
    assert data["is_private"] is True
    assert data["is_global_public"] is False
    
    # Clean up the created todo
    todo_id = data["id"]
    cleanup_response = client.delete(f"/todos/{todo_id}", headers=headers)
    assert cleanup_response.status_code == 200

def test_create_todo_with_global_public(client, unique_test_user):
    """Test creating a global public todo via API."""
    user, token = unique_test_user
    headers = {"Authorization": f"Bearer {token}"}
    
    todo_payload = {
        "title": "Global Public Todo",
        "description": "This should be visible to everyone",
        "is_private": False,
        "is_global_public": True
    }
    
    response = client.post("/todos/", headers=headers, json=todo_payload)
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}. Response: {response.text}"
    
    data = response.json()
    assert data["title"] == todo_payload["title"]
    assert data["is_private"] is False
    assert data["is_global_public"] is True
    
    # Clean up the created todo
    todo_id = data["id"]
    cleanup_response = client.delete(f"/todos/{todo_id}", headers=headers)
    assert cleanup_response.status_code == 200

def test_create_todo_with_default_privacy_settings(client, unique_test_user):
    """Test creating a todo without specifying privacy fields (should use defaults)."""
    user, token = unique_test_user
    headers = {"Authorization": f"Bearer {token}"}
    
    todo_payload = {
        "title": "Default Privacy Todo",
        "description": "Should use default privacy settings"
    }
    
    response = client.post("/todos/", headers=headers, json=todo_payload)
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}. Response: {response.text}"
    
    data = response.json()
    assert data["title"] == todo_payload["title"]
    # Should default to private=True, global_public=False
    assert data["is_private"] is True
    assert data["is_global_public"] is False
    
    # Clean up the created todo
    todo_id = data["id"]
    cleanup_response = client.delete(f"/todos/{todo_id}", headers=headers)
    assert cleanup_response.status_code == 200 