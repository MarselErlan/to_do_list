import pytest
import requests
from fastapi.testclient import TestClient
from datetime import date
from app import crud, schemas
from sqlalchemy.orm import Session

@pytest.mark.sanity
class TestAPISanity:
    """Sanity tests for critical API functionality"""
    
    def test_api_health_check(self, client: TestClient):
        """Sanity: Verify API is responsive and returns basic info"""
        response = client.get("/docs")
        assert response.status_code == 200
        
    def test_get_empty_todos_list(self, client: TestClient, authenticated_headers: dict):
        """Sanity: Verify we can retrieve empty todos list for a new user"""
        response = client.get("/todos/", headers=authenticated_headers)
        assert response.status_code == 200
        assert response.json() == []
        
    def test_create_todo_basic(self, client: TestClient, sample_todo: dict, authenticated_headers: dict):
        """Sanity: Verify we can create a basic todo"""
        response = client.post("/todos/", json=sample_todo, headers=authenticated_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["title"] == sample_todo["title"]
        assert data["description"] == sample_todo["description"]
        assert data["done"] == sample_todo["done"]
        assert "id" in data
        
    def test_get_todo_by_id(self, client: TestClient, sample_todo: dict, authenticated_headers: dict):
        """Sanity: Verify we can retrieve a specific todo by ID"""
        # Create a todo first
        create_response = client.post("/todos/", json=sample_todo, headers=authenticated_headers)
        assert create_response.status_code == 200
        todo_id = create_response.json()["id"]
        
        # Retrieve it
        get_response = client.get(f"/todos/{todo_id}", headers=authenticated_headers)
        assert get_response.status_code == 200
        
        data = get_response.json()
        assert data["id"] == todo_id
        assert data["title"] == sample_todo["title"]
        
    def test_update_todo_basic(self, client: TestClient, sample_todo: dict, authenticated_headers: dict):
        """Sanity: Verify we can update a todo"""
        # Create a todo
        create_response = client.post("/todos/", json=sample_todo, headers=authenticated_headers)
        assert create_response.status_code == 200
        todo_id = create_response.json()["id"]
        
        # Update it
        update_data = {"title": "Updated Sanity Todo", "done": True}
        update_response = client.put(f"/todos/{todo_id}", json=update_data, headers=authenticated_headers)
        assert update_response.status_code == 200
        
        data = update_response.json()
        assert data["title"] == "Updated Sanity Todo"
        assert data["done"] is True
        
    def test_delete_todo_basic(self, client: TestClient, sample_todo: dict, authenticated_headers: dict):
        """Sanity: Verify we can delete a todo"""
        # Create a todo
        create_response = client.post("/todos/", json=sample_todo, headers=authenticated_headers)
        assert create_response.status_code == 200
        todo_id = create_response.json()["id"]
        
        # Delete it
        delete_response = client.delete(f"/todos/{todo_id}", headers=authenticated_headers)
        assert delete_response.status_code == 200
        
        # Verify it's gone
        get_response = client.get(f"/todos/{todo_id}", headers=authenticated_headers)
        assert get_response.status_code == 404
        
    @pytest.mark.regression
    def test_complete_todo_workflow(self, client: TestClient, authenticated_headers: dict):
        """Sanity: Test complete CRUD workflow in one go"""
        # Create
        todo_data = {
            "title": "Complete Workflow Test",
            "description": "Testing the complete workflow",
            "done": False
        }
        
        create_response = client.post("/todos/", json=todo_data, headers=authenticated_headers)
        assert create_response.status_code == 200
        todo_id = create_response.json()["id"]
        
        # Read (list)
        list_response = client.get("/todos/", headers=authenticated_headers)
        assert list_response.status_code == 200
        assert len(list_response.json()) == 1 # Should be exactly 1 for a new user
        
        # Read (single)
        get_response = client.get(f"/todos/{todo_id}", headers=authenticated_headers)
        assert get_response.status_code == 200
        
        # Update
        update_response = client.put(f"/todos/{todo_id}", json={"done": True}, headers=authenticated_headers)
        assert update_response.status_code == 200
        assert update_response.json()["done"] is True
        
        # Delete
        delete_response = client.delete(f"/todos/{todo_id}", headers=authenticated_headers)
        assert delete_response.status_code == 200
        
        # Verify deletion
        final_get = client.get(f"/todos/{todo_id}", headers=authenticated_headers)
        assert final_get.status_code == 404

    @pytest.mark.regression
    def test_time_management_endpoints_sanity(self, client: TestClient, authenticated_headers: dict):
        """Sanity: Verify time management endpoints are accessible"""
        from datetime import date
        
        # Test all time management endpoints exist and return 200
        endpoints = [
            "/todos/today",
            "/todos/week", 
            "/todos/month",
            "/todos/year",
            "/todos/overdue"
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint, headers=authenticated_headers)
            assert response.status_code == 200
            assert isinstance(response.json(), list)
        
        # Test date range endpoint
        today = date.today()
        range_response = client.get(f"/todos/range?start_date={today}&end_date={today}", headers=authenticated_headers)
        assert range_response.status_code == 200
        assert isinstance(range_response.json(), list)

    def test_create_todo_with_time_fields_sanity(self, client: TestClient, authenticated_headers: dict):
        """Sanity: Verify we can create todos with time fields"""
        from datetime import date
        
        todo_with_time = {
            "title": "Sanity Time Todo",
            "description": "Testing time fields",
            "start_date": "2024-12-25",
            "start_time": "09:00:00",
            "due_date": date.today().isoformat()
        }
        
        response = client.post("/todos/", json=todo_with_time, headers=authenticated_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["title"] == "Sanity Time Todo"
        assert data["start_date"] == "2024-12-25"
        assert data["start_time"] == "09:00:00"
        assert data["due_date"] == date.today().isoformat()

@pytest.mark.sanity
@pytest.mark.live
class TestLiveAPISanity:
    """Sanity tests against live API deployment"""
    
    @pytest.mark.regression
    def test_live_api_health(self, live_api_url):
        """Sanity: Verify live API is accessible"""
        try:
            response = requests.get(f"{live_api_url}/health", timeout=10)
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}
        except requests.RequestException as e:
            pytest.skip(f"Live API not accessible: {e}")
            
    @pytest.mark.skip(reason="CORS is verified manually and via UI tests; this test is brittle.")
    def test_live_api_cors_headers(self, live_api_url):
        """Sanity: Verify CORS headers are present for frontend"""
        try:
            response = requests.options(f"{live_api_url}/health", timeout=10)
            assert response.status_code in [200, 204]
            
            headers = response.headers
            assert "access-control-allow-origin" in headers
            
        except requests.RequestException as e:
            pytest.skip(f"Live API not accessible: {e}")

    @pytest.mark.skip(reason="Live time management endpoints require authentication and are not suitable for a simple health check.")
    def test_live_time_management_endpoints(self, live_api_url):
        """Sanity: Verify live time management endpoints work"""
        try:
            endpoints = ["/todos/today", "/todos/week", "/todos/month", "/todos/year", "/todos/overdue"]
            
            for endpoint in endpoints:
                response = requests.get(f"{live_api_url}{endpoint}", timeout=10)
                assert response.status_code == 200
                assert isinstance(response.json(), list)
                
        except requests.RequestException as e:
            pytest.skip(f"Live API not accessible: {e}") 