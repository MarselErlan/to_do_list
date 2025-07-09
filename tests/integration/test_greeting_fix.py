import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app import crud, models, schemas
from app.llm_service import TaskDetails


@patch("app.llm_service.ChatOpenAI")
@patch("langchain_core.runnables.base.RunnableSequence.invoke")
def test_greeting_returns_json_clarification(
    mock_chain_invoke: MagicMock,
    mock_chat_openai: MagicMock,
    client: TestClient,
    db: Session,
    test_user_token_headers: dict
):
    """
    Tests that greeting messages like 'hello' return proper JSON clarification
    instead of plain text, preventing the JSON parsing error.
    """
    # 1. Setup: Get user
    response = client.get("/users/me", headers=test_user_token_headers)
    assert response.status_code == 200
    current_user = schemas.User(**response.json())

    # 2. Mock the LLM to return proper JSON structure for greeting
    mock_chain_invoke.return_value = TaskDetails(
        task_title=None,
        clarification_questions=["Hello! How can I help you create a task? What would you like to do?"],
        is_complete=False
    )
    
    # 3. Call the API with a greeting message
    history = [{"sender": "user", "text": "hello"}]
    with TestClient(app) as client:
        response = client.post(
            "/chat/create-task",
            headers=test_user_token_headers,
            json={"history": history}
        )
    
    # 4. Assert that the API returns proper JSON (not 500 error)
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["is_complete"] is False
    assert "task_title" in response_data
    assert response_data["task_title"] is None
    assert "clarification_questions" in response_data
    assert len(response_data["clarification_questions"]) > 0
    assert "task" in response_data["clarification_questions"][0].lower()


@patch("app.llm_service.ChatOpenAI")
@patch("langchain_core.runnables.base.RunnableSequence.invoke")
def test_hi_returns_json_clarification(
    mock_chain_invoke: MagicMock,
    mock_chat_openai: MagicMock,
    client: TestClient,
    db: Session,
    test_user_token_headers: dict
):
    """
    Tests that other greeting messages like 'hi' also return proper JSON.
    """
    # 1. Setup: Get user
    response = client.get("/users/me", headers=test_user_token_headers)
    assert response.status_code == 200
    current_user = schemas.User(**response.json())

    # 2. Mock the LLM to return proper JSON structure for greeting
    mock_chain_invoke.return_value = TaskDetails(
        task_title=None,
        clarification_questions=["Hi there! What task would you like to create?"],
        is_complete=False
    )
    
    # 3. Call the API with a greeting message
    history = [{"sender": "user", "text": "hi"}]
    with TestClient(app) as client:
        response = client.post(
            "/chat/create-task",
            headers=test_user_token_headers,
            json={"history": history}
        )
    
    # 4. Assert that the API returns proper JSON (not 500 error)
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["is_complete"] is False
    assert "task_title" in response_data
    assert response_data["task_title"] is None
    assert "clarification_questions" in response_data
    assert len(response_data["clarification_questions"]) > 0
