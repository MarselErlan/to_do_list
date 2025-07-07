"""
TDD Tests for /todos/ endpoint
Testing global todos functionality, authentication, and CRUD operations
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, date, time
import json

from app import crud, schemas, models
from app.security import create_access_token

class TestTodosEndpointTDD:
    """TDD tests for /todos/ endpoint using existing test fixtures"""

    def test_get_todos_requires_authentication(self, client: TestClient):
        """Test that GET /todos/ requires authentication"""
        response = client.get("/todos/")
        assert response.status_code == 401
        assert "Not authenticated" in response.json()["detail"]

    def test_post_todos_requires_authentication(self, client: TestClient):
        """Test that POST /todos/ requires authentication"""
        todo_data = {
            "title": "Test Todo",
            "description": "Test description"
        }
        response = client.post("/todos/", json=todo_data)
        assert response.status_code == 401
        assert "Not authenticated" in response.json()["detail"]

    def test_create_todo_basic(self, authenticated_client: TestClient):
        """Test basic todo creation"""
        todo_data = {
            "title": "Test Todo",
            "description": "Test description",
            "done": False
        }
        response = authenticated_client.post("/todos/", json=todo_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["title"] == "Test Todo"
        assert data["description"] == "Test description"
        assert data["done"] is False
        assert "id" in data
        assert "owner_id" in data
        assert "created_at" in data

    def test_create_todo_with_dates(self, authenticated_client: TestClient):
        """Test todo creation with date/time fields"""
        todo_data = {
            "title": "Scheduled Todo",
            "description": "Todo with dates",
            "start_date": "2024-01-15",
            "start_time": "09:00:00",
            "end_date": "2024-01-15",
            "end_time": "17:00:00",
            "due_date": "2024-01-14"
        }
        response = authenticated_client.post("/todos/", json=todo_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["title"] == "Scheduled Todo"
        assert data["start_date"] == "2024-01-15"
        assert data["start_time"] == "09:00:00"
        assert data["end_date"] == "2024-01-15"
        assert data["end_time"] == "17:00:00"
        assert data["due_date"] == "2024-01-14"

    def test_create_global_public_todo(self, authenticated_client: TestClient):
        """Test creation of global public todo"""
        todo_data = {
            "title": "Global Public Todo",
            "description": "This should be visible to everyone",
            "is_global_public": True,
            "is_private": False
        }
        response = authenticated_client.post("/todos/", json=todo_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["title"] == "Global Public Todo"
        assert data["is_global_public"] is True
        assert data["is_private"] is False

    def test_create_private_todo(self, authenticated_client: TestClient):
        """Test creation of private todo"""
        todo_data = {
            "title": "Private Todo",
            "description": "This should be private",
            "is_private": True,
            "is_global_public": False
        }
        response = authenticated_client.post("/todos/", json=todo_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["title"] == "Private Todo"
        assert data["is_private"] is True
        assert data["is_global_public"] is False

    def test_get_todos_empty_list(self, authenticated_client: TestClient):
        """Test getting todos when none exist"""
        response = authenticated_client.get("/todos/")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_todos_with_data(self, authenticated_client: TestClient, db: Session):
        """Test getting todos when data exists"""
        # Create some todos first
        todo1_data = {"title": "Todo 1", "description": "First todo"}
        todo2_data = {"title": "Todo 2", "description": "Second todo"}
        
        authenticated_client.post("/todos/", json=todo1_data)
        authenticated_client.post("/todos/", json=todo2_data)
        
        response = authenticated_client.get("/todos/")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) == 2
        
        # Check that both todos are returned
        titles = [todo["title"] for todo in data]
        assert "Todo 1" in titles
        assert "Todo 2" in titles

    def test_get_todos_pagination(self, authenticated_client: TestClient):
        """Test todos pagination with skip and limit"""
        # Create multiple todos
        for i in range(5):
            todo_data = {"title": f"Todo {i+1}", "description": f"Todo number {i+1}"}
            authenticated_client.post("/todos/", json=todo_data)
        
        # Test with limit
        response = authenticated_client.get("/todos/?limit=3")
        assert response.status_code == 200
        assert len(response.json()) == 3
        
        # Test with skip
        response = authenticated_client.get("/todos/?skip=2")
        assert response.status_code == 200
        assert len(response.json()) == 3
        
        # Test with skip and limit
        response = authenticated_client.get("/todos/?skip=1&limit=2")
        assert response.status_code == 200
        assert len(response.json()) == 2

    def test_get_todos_user_isolation(self, client: TestClient, db: Session):
        """Test that users only see their own todos"""
        # Create two users
        user1_data = schemas.UserCreate(username="user1", password="pass1", email="user1@test.com")
        user2_data = schemas.UserCreate(username="user2", password="pass2", email="user2@test.com")
        
        user1 = crud.create_user(db, user1_data)
        user2 = crud.create_user(db, user2_data)
        
        # Create todos for each user
        crud.create_todo(db=db, todo=schemas.TodoCreate(title="User1 Todo"), owner_id=user1.id)
        crud.create_todo(db=db, todo=schemas.TodoCreate(title="User2 Todo"), owner_id=user2.id)
        
        # Test user1 only sees their todo
        login_data = {"username": "user1", "password": "pass1"}
        response = client.post("/token", data=login_data)
        assert response.status_code == 200
        token1 = response.json()["access_token"]
        headers1 = {"Authorization": f"Bearer {token1}"}
        
        response = client.get("/todos/", headers=headers1)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "User1 Todo"

    def test_get_specific_todo_by_id(self, authenticated_client: TestClient):
        """Test getting a specific todo by ID"""
        # Create a todo
        todo_data = {"title": "Specific Todo", "description": "Test todo"}
        response = authenticated_client.post("/todos/", json=todo_data)
        assert response.status_code == 200
        todo_id = response.json()["id"]
        
        response = authenticated_client.get(f"/todos/{todo_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == todo_id
        assert data["title"] == "Specific Todo"
        assert data["description"] == "Test todo"

    def test_get_todo_not_found(self, authenticated_client: TestClient):
        """Test getting a todo that doesn't exist"""
        response = authenticated_client.get("/todos/999")
        assert response.status_code == 404
        assert "Todo not found" in response.json()["detail"]

    def test_get_todo_permission_denied(self, client: TestClient, db: Session):
        """Test that users cannot access other users' todos"""
        # Create two users
        user1_data = schemas.UserCreate(username="user1", password="pass1", email="user1@test.com")
        user2_data = schemas.UserCreate(username="user2", password="pass2", email="user2@test.com")
        
        user1 = crud.create_user(db, user1_data)
        user2 = crud.create_user(db, user2_data)
        
        # User1 creates a todo
        todo = crud.create_todo(
            db=db,
            todo=schemas.TodoCreate(title="User1 Todo"),
            owner_id=user1.id
        )
        
        # User2 tries to access user1's todo
        login_data = {"username": "user2", "password": "pass2"}
        response = client.post("/token", data=login_data)
        assert response.status_code == 200
        token2 = response.json()["access_token"]
        headers2 = {"Authorization": f"Bearer {token2}"}
        
        response = client.get(f"/todos/{todo.id}", headers=headers2)
        assert response.status_code == 403
        assert "Not enough permissions" in response.json()["detail"]

    def test_update_todo(self, authenticated_client: TestClient):
        """Test updating a todo"""
        # Create a todo
        todo_data = {"title": "Original Title", "description": "Original description"}
        response = authenticated_client.post("/todos/", json=todo_data)
        assert response.status_code == 200
        todo_id = response.json()["id"]
        
        # Update the todo
        update_data = {
            "title": "Updated Title",
            "description": "Updated description",
            "done": True
        }
        response = authenticated_client.put(f"/todos/{todo_id}", json=update_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["title"] == "Updated Title"
        assert data["description"] == "Updated description"
        assert data["done"] is True

    def test_update_todo_not_found(self, authenticated_client: TestClient):
        """Test updating a todo that doesn't exist"""
        update_data = {"title": "Updated Title"}
        response = authenticated_client.put("/todos/999", json=update_data)
        assert response.status_code == 404
        assert "Todo not found" in response.json()["detail"]

    def test_delete_todo(self, authenticated_client: TestClient):
        """Test deleting a todo"""
        # Create a todo
        todo_data = {"title": "To Delete", "description": "This will be deleted"}
        response = authenticated_client.post("/todos/", json=todo_data)
        assert response.status_code == 200
        todo_id = response.json()["id"]
        
        # Delete the todo
        response = authenticated_client.delete(f"/todos/{todo_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["title"] == "To Delete"
        
        # Verify todo is deleted
        response = authenticated_client.get(f"/todos/{todo_id}")
        assert response.status_code == 404

    def test_delete_todo_not_found(self, authenticated_client: TestClient):
        """Test deleting a todo that doesn't exist"""
        response = authenticated_client.delete("/todos/999")
        assert response.status_code == 404
        assert "Todo not found" in response.json()["detail"]

    def test_create_todo_invalid_data(self, authenticated_client: TestClient):
        """Test creating todo with invalid data"""
        # Test missing required title
        todo_data = {
            "description": "No title provided"
        }
        response = authenticated_client.post("/todos/", json=todo_data)
        assert response.status_code == 422
        
        # Test invalid date format
        todo_data = {
            "title": "Invalid Date",
            "due_date": "invalid-date"
        }
        response = authenticated_client.post("/todos/", json=todo_data)
        assert response.status_code == 422

    def test_global_todos_visibility_scenario(self, authenticated_client: TestClient):
        """Test the global todos visibility scenario from the frontend issue"""
        # Create a global public todo
        global_todo_data = {
            "title": "Global Public Todo",
            "description": "Should be visible to everyone",
            "is_global_public": True,
            "is_private": False
        }
        response = authenticated_client.post("/todos/", json=global_todo_data)
        assert response.status_code == 200
        
        # Create a private todo
        private_todo_data = {
            "title": "Private Todo",
            "description": "Should be private",
            "is_private": True,
            "is_global_public": False
        }
        response = authenticated_client.post("/todos/", json=private_todo_data)
        assert response.status_code == 200
        
        # Get all todos for the user
        response = authenticated_client.get("/todos/")
        assert response.status_code == 200
        data = response.json()
        
        # Should see both todos
        assert len(data) == 2
        titles = [todo["title"] for todo in data]
        assert "Global Public Todo" in titles
        assert "Private Todo" in titles
        
        # Verify global todo properties
        global_todo = next(todo for todo in data if todo["title"] == "Global Public Todo")
        assert global_todo["is_global_public"] is True
        assert global_todo["is_private"] is False
        
        # Verify private todo properties
        private_todo = next(todo for todo in data if todo["title"] == "Private Todo")
        assert private_todo["is_private"] is True
        assert private_todo["is_global_public"] is False

    def test_todos_endpoint_comprehensive_flow(self, authenticated_client: TestClient):
        """Test a comprehensive flow of CRUD operations"""
        # 1. Start with empty list
        response = authenticated_client.get("/todos/")
        assert response.status_code == 200
        assert len(response.json()) == 0
        
        # 2. Create a todo
        todo_data = {
            "title": "Comprehensive Test Todo",
            "description": "Testing full CRUD flow",
            "due_date": "2024-12-31"
        }
        response = authenticated_client.post("/todos/", json=todo_data)
        assert response.status_code == 200
        todo_id = response.json()["id"]
        
        # 3. Verify it appears in the list
        response = authenticated_client.get("/todos/")
        assert response.status_code == 200
        assert len(response.json()) == 1
        
        # 4. Get the specific todo
        response = authenticated_client.get(f"/todos/{todo_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Comprehensive Test Todo"
        assert data["done"] is False
        
        # 5. Update the todo
        update_data = {
            "title": "Updated Comprehensive Todo",
            "done": True
        }
        response = authenticated_client.put(f"/todos/{todo_id}", json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Comprehensive Todo"
        assert data["done"] is True
        
        # 6. Delete the todo
        response = authenticated_client.delete(f"/todos/{todo_id}")
        assert response.status_code == 200
        
        # 7. Verify it's gone
        response = authenticated_client.get("/todos/")
        assert response.status_code == 200
        assert len(response.json()) == 0
