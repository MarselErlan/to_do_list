import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app import crud, models, schemas
from app.llm_service import TaskDetails


@patch("app.llm_service.ChatOpenAI")
@patch("langchain_core.runnables.base.RunnableSequence.invoke")
def test_chat_create_task_in_team_workspace(
    mock_chain_invoke: MagicMock,
    mock_chat_openai: MagicMock,
    client: TestClient, 
    db: Session, 
    test_user_token_headers: dict
):
    """
    Tests creating a task that should be assigned to a team workspace (Session).
    Mocks the LLM chain's invoke method and the ChatOpenAI instantiation.
    """
    # 1. Setup: Get the current user and create a session for them
    response = client.get("/users/me", headers=test_user_token_headers)
    assert response.status_code == 200
    current_user = schemas.User(**response.json())
    team_session = crud.create_team_session(db, session=schemas.SessionCreate(name="Engineering Team"), owner_id=current_user.id)

    # 2. Mock the chain's return value
    mock_chain_invoke.return_value = TaskDetails(
        task_title="Deploy staging server",
        description="Deploy the latest code to the staging environment for testing.",
        session_name="Engineering Team"
    )
    
    # 3. Call the API
    with TestClient(app) as api_client:
        response = api_client.post(
            "/chat/create-task",
            headers=test_user_token_headers,
            json={"user_query": "Does not matter, as invoke is mocked"}
        )

    # 4. Assertions
    assert response.status_code == 200
    
    # Verify the task was created in the database and linked to the correct session
    todos = crud.get_todos_by_user(db, user_id=current_user.id)
    assert len(todos) == 1
    created_todo = todos[0]
    assert created_todo.title == "Deploy staging server"
    assert created_todo.session_id == team_session.id
    assert created_todo.session.name == "Engineering Team"


@patch("app.llm_service.ChatOpenAI")
@patch("langchain_core.runnables.base.RunnableSequence.invoke")
def test_chat_create_task_in_personal_workspace(
    mock_chain_invoke: MagicMock,
    mock_chat_openai: MagicMock,
    client: TestClient, 
    db: Session, 
    test_user_token_headers: dict
):
    """
    Tests creating a task that should be assigned to a personal workspace (no Session).
    Mocks the LLM chain's invoke method and the ChatOpenAI instantiation.
    """
    # 1. Get the current user
    response = client.get("/users/me", headers=test_user_token_headers)
    assert response.status_code == 200
    current_user = schemas.User(**response.json())

    # 2. Mock the chain's return value
    mock_chain_invoke.return_value = TaskDetails(
        task_title="Update my personal resume",
        description="Add new skills and recent projects.",
        session_name=None  # Explicitly no session
    )
    
    # 3. Call the API
    with TestClient(app) as api_client:
        response = api_client.post(
            "/chat/create-task",
            headers=test_user_token_headers,
            json={"user_query": "Does not matter, as invoke is mocked"}
        )

    # 4. Assertions
    assert response.status_code == 200
    
    # Verify the task was created and is NOT linked to a session, but to the user's private session
    private_session = db.query(models.Session).filter(
        models.Session.created_by_id == current_user.id,
        models.Session.name == None
    ).one()

    todos = crud.get_todos_by_user(db, user_id=current_user.id)
    assert len(todos) == 1
    created_todo = todos[0]
    assert created_todo.title == "Update my personal resume"
    assert created_todo.session_id == private_session.id 