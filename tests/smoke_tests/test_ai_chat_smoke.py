"""
Smoke tests for AI Chat functionality.
These tests ensure the AI-powered task creation works for critical scenarios.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import patch, MagicMock


def get_auth_headers(client: TestClient, username: str, password: str) -> dict:
    """Helper to create user and get auth headers."""
    user_data = {"username": username, "email": f"{username}@test.com", "password": password}
    client.post("/users/", json=user_data)
    
    token_response = client.post("/token", data={"username": username, "password": password})
    token = token_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.smoke
def test_smoke_ai_chat_basic_task_creation(client: TestClient, db: Session):
    """
    Critical path: AI can create a basic task from natural language
    """
    # Mock the global task_creation_graph
    mock_graph = MagicMock()
    mock_graph.invoke.return_value = {
        "task_title": "Buy groceries", 
        "description": "Get milk and bread",
        "is_private": True,
        "is_complete": True,
        "clarification_questions": []
    }
    
    with patch('app.main.task_creation_graph', mock_graph):
        headers = get_auth_headers(client, "smoke_ai_user", "aipass")
        
        chat_request = {
            "history": [{"sender": "user", "text": "I need to buy groceries"}],
            "current_session_id": None
        }
        
        response = client.post("/chat/create-task", json=chat_request, headers=headers)
        assert response.status_code == 200
        
        result = response.json()
        assert result.get("is_complete") is True
        assert "task_title" in result


@pytest.mark.smoke
def test_smoke_ai_chat_handles_greetings(client: TestClient, db: Session):
    """
    Critical path: AI handles conversational greetings appropriately
    """
    # Mock the global task_creation_graph for greeting response
    mock_graph = MagicMock()
    mock_graph.invoke.return_value = {
        "is_complete": False,
        "clarification_questions": ["Hello! How can I help you create a task today?"],
        "conversation_response": "Hello! How can I help you create a task today?"
    }
    
    with patch('app.main.task_creation_graph', mock_graph):
        headers = get_auth_headers(client, "smoke_greeting_user", "greetpass")
        
        chat_request = {
            "history": [{"sender": "user", "text": "Hello"}],
            "current_session_id": None
        }
        
        response = client.post("/chat/create-task", json=chat_request, headers=headers)
        assert response.status_code == 200
        
        result = response.json()
        # Should not complete a task for greeting
        assert result.get("is_complete") is False
        # Should provide a friendly response
        assert "clarification_questions" in result


@pytest.mark.smoke
def test_smoke_ai_chat_error_handling(client: TestClient, db: Session):
    """
    Critical path: AI chat gracefully handles errors and returns valid JSON
    """
    # Mock the global task_creation_graph to simulate error recovery
    mock_graph = MagicMock()
    mock_graph.invoke.return_value = {
        "is_complete": False,
        "clarification_questions": ["I need more information to create a task."],
        "user_query": ""
    }
    
    with patch('app.main.task_creation_graph', mock_graph):
        headers = get_auth_headers(client, "smoke_error_user", "errorpass")
        
        # Send request that might cause issues
        chat_request = {
            "history": [],  # Empty history
            "current_session_id": 99999  # Non-existent session
        }
        
        response = client.post("/chat/create-task", json=chat_request, headers=headers)
        assert response.status_code == 200  # Should not crash
        
        result = response.json()
        # Should always return valid JSON structure
        assert "is_complete" in result
        assert isinstance(result["is_complete"], bool) 