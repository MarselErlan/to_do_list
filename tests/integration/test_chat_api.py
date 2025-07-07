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

@patch("app.llm_service.ChatOpenAI")
@patch("langchain_core.runnables.base.RunnableSequence.invoke")
def test_chat_create_task_implicit_team_workspace(
    mock_chain_invoke: MagicMock,
    mock_chat_openai: MagicMock,
    client: TestClient, 
    db: Session, 
    test_user_token_headers: dict
):
    """
    Tests creating a task in the *current* team workspace when no specific
    workspace is mentioned in the query.
    """
    # 1. Setup
    response = client.get("/users/me", headers=test_user_token_headers)
    current_user = schemas.User(**response.json())
    current_session = crud.create_team_session(db, session=schemas.SessionCreate(name="Design Team"), owner_id=current_user.id)

    # 2. Mock the LLM to return a task title but NO session_name,
    # because the user query is implicit.
    mock_chain_invoke.return_value = TaskDetails(
        task_title="Review new wireframes",
        description="Check the latest designs for the new feature."
    )
    
    # 3. Call the API, passing the current_session_id
    response = client.post(
        "/chat/create-task",
        headers=test_user_token_headers,
        json={
            "user_query": "Review the new wireframes",
            "current_session_id": current_session.id
        }
    )

    # 4. Assertions
    assert response.status_code == 200
    
    todos = crud.get_todos_by_session(db, session_id=current_session.id, requesting_user_id=current_user.id)
    assert len(todos) == 1
    created_todo = todos[0]
    assert created_todo.title == "Review new wireframes"
    assert created_todo.session_id == current_session.id 

@patch("app.llm_service.ChatOpenAI")
@patch("langchain_core.runnables.base.RunnableSequence.invoke")
def test_chat_create_task_explicit_different_team_workspace(
    mock_chain_invoke: MagicMock,
    mock_chat_openai: MagicMock,
    client: TestClient,
    db: Session,
    test_user_token_headers: dict
):
    """
    Tests creating a task in a DIFFERENT team workspace from the one the
    user is currently in, by explicitly mentioning it in the query.
    """
    # 1. Setup
    response = client.get("/users/me", headers=test_user_token_headers)
    current_user = schemas.User(**response.json())
    current_session = crud.create_team_session(db, session=schemas.SessionCreate(name="General"), owner_id=current_user.id)
    target_session = crud.create_team_session(db, session=schemas.SessionCreate(name="Marketing"), owner_id=current_user.id)

    # 2. Mock the LLM to return the *target* session name
    mock_chain_invoke.return_value = TaskDetails(
        task_title="Draft Q3 social media plan",
        session_name="Marketing"
    )

    # 3. Call the API, passing the *current* session_id
    response = client.post(
        "/chat/create-task",
        headers=test_user_token_headers,
        json={
            "user_query": "For the Marketing workspace, draft the Q3 social media plan",
            "current_session_id": current_session.id
        }
    )

    # 4. Assertions
    assert response.status_code == 200

    # The task should be in the 'Marketing' session, not 'General'
    target_todos = crud.get_todos_by_session(db, session_id=target_session.id, requesting_user_id=current_user.id)
    assert len(target_todos) == 1
    assert target_todos[0].title == "Draft Q3 social media plan"

    current_todos = crud.get_todos_by_session(db, session_id=current_session.id, requesting_user_id=current_user.id)
    assert len(current_todos) == 0

@patch("app.llm_service.ChatOpenAI")
@patch("langchain_core.runnables.base.RunnableSequence.invoke")
def test_chat_create_task_global_public(
    mock_chain_invoke: MagicMock,
    mock_chat_openai: MagicMock,
    client: TestClient,
    db: Session,
    test_user_token_headers: dict
):
    """
    Tests creating a task that is marked as globally public.
    """
    # 1. Setup
    response = client.get("/users/me", headers=test_user_token_headers)
    current_user = schemas.User(**response.json())

    # 2. Mock the LLM to return `is_global_public=True`
    mock_chain_invoke.return_value = TaskDetails(
        task_title="Announce company-wide holiday",
        is_global_public=True
    )

    # 3. Call the API
    response = client.post(
        "/chat/create-task",
        headers=test_user_token_headers,
        json={"user_query": "Announce the company-wide holiday to everyone"}
    )

    # 4. Assertions
    assert response.status_code == 200

    # The task should be marked as globally public
    # It will be in the user's private session by default
    todos = crud.get_todos_by_user(db, user_id=current_user.id)
    assert len(todos) == 1
    created_todo = todos[0]
    assert created_todo.title == "Announce company-wide holiday"
    assert created_todo.is_global_public is True
    assert created_todo.is_private is False # Global tasks cannot be private 

@patch("app.llm_service.ChatOpenAI")
@patch("langchain_core.runnables.base.RunnableSequence.invoke")
def test_chat_create_task_clarification_loop(
    mock_chain_invoke: MagicMock,
    mock_chat_openai: MagicMock,
    client: TestClient,
    db: Session,
    test_user_token_headers: dict
):
    """
    Tests that the API returns a clarification question if the task title
    cannot be determined from the user's query.
    """
    # 1. Setup
    response = client.get("/users/me", headers=test_user_token_headers)
    current_user = schemas.User(**response.json())

    # 2. Mock the LLM to return an incomplete result (no title)
    mock_chain_invoke.return_value = TaskDetails(
        description="A meeting about the project"
    )

    # 3. Call the API
    response = client.post(
        "/chat/create-task",
        headers=test_user_token_headers,
        json={"user_query": "schedule a meeting about the project"}
    )

    # 4. Assertions
    assert response.status_code == 200
    response_data = response.json()
    
    # Check for the clarification question in the response
    assert response_data["is_complete"] is False
    assert "I'm sorry, I couldn't determine a task title. What is the task?" in response_data["clarification_questions"]

    # Verify that no task was created
    todos = crud.get_todos_by_user(db, user_id=current_user.id)
    assert len(todos) == 0 