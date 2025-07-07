import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app import crud, models, schemas
from app.llm_service import TaskDetails


@patch("app.llm_service.ChatOpenAI")
@patch("langchain_core.runnables.base.RunnableSequence.invoke")
def test_chat_create_task_with_conversation_history(
    mock_chain_invoke: MagicMock,
    mock_chat_openai: MagicMock,
    client: TestClient,
    db: Session,
    test_user_token_headers: dict
):
    """
    Tests creating a task over a multi-turn conversation, relying on langgraph state.
    """
    # 1. Setup: Get user
    response = client.get("/users/me", headers=test_user_token_headers)
    assert response.status_code == 200
    current_user = schemas.User(**response.json())

    # --- Turn 1: User is unclear ---
    
    # 2. Mock the LLM to ask for clarification
    mock_chain_invoke.return_value = TaskDetails(
        clarification_questions=["What is the title of the task?"]
    )
    
    # 3. Call the API with an incomplete query
    history1 = [{"sender": "user", "text": "I want to make a task"}]
    with TestClient(app) as client:
        response1 = client.post(
            "/chat/create-task",
            headers=test_user_token_headers,
            json={"history": history1}
        )
    
    # 4. Assert that the API asks for clarification
    assert response1.status_code == 200
    response_data1 = response1.json()
    assert response_data1["is_complete"] is False
    assert "I'm sorry, I couldn't determine a task title. What is the task?" in response_data1["clarification_questions"]

    # --- Turn 2: User provides the title ---

    # 5. Mock the LLM to successfully create the task now
    mock_chain_invoke.return_value = TaskDetails(
        task_title="Buy groceries",
        description="Milk, bread, and eggs",
        is_complete=True
    )
    
    # 6. Call the API again with the full history
    history2 = history1 + [
        {"sender": "ai", "text": "I'm sorry, I couldn't determine a task title. What is the task?"},
        {"sender": "user", "text": "The title is 'Buy groceries' and please add a description: Milk, bread, and eggs"}
    ]
    with TestClient(app) as client:
        response2 = client.post(
            "/chat/create-task",
            headers=test_user_token_headers,
            json={"history": history2}
        )

    # 7. Assert that the task was created successfully
    assert response2.status_code == 200
    response_data2 = response2.json()
    assert response_data2["is_complete"] is True
    
    # 8. Verify the task in the database
    todos = crud.get_todos_by_user(db, user_id=current_user.id)
    assert len(todos) == 1
    created_todo = todos[0]
    assert created_todo.title == "Buy groceries"
    assert created_todo.description == "Milk, bread, and eggs"


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
            json={"history": [{"sender": "user", "text": "Does not matter, as invoke is mocked"}]}
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
            json={"history": [{"sender": "user", "text": "Does not matter, as invoke is mocked"}]}
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
    with TestClient(app) as client:
        response = client.post(
            "/chat/create-task",
            headers=test_user_token_headers,
            json={
                "history": [{"sender": "user", "text": "Review the new wireframes"}],
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
    with TestClient(app) as client:
        response = client.post(
            "/chat/create-task",
            headers=test_user_token_headers,
            json={
                "history": [{"sender": "user", "text": "For the Marketing workspace, draft the Q3 social media plan"}],
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
    with TestClient(app) as client:
        response = client.post(
            "/chat/create-task",
            headers=test_user_token_headers,
            json={"history": [{"sender": "user", "text": "Announce the company-wide holiday to everyone"}]}
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
def test_chat_create_task_single_team_general_request(
    mock_chain_invoke: MagicMock,
    mock_chat_openai: MagicMock,
    client: TestClient, 
    db: Session, 
    test_user_token_headers: dict
):
    """
    Tests that if a user is in only one team, a general request 'for the team'
    correctly assigns the task to that single team.
    """
    # 1. Setup: Create a second user and a single team for the main user
    # Note: We assume the test_user fixture creates a user, but we may need
    # to create another session for them.
    with Session(db.get_bind(), expire_on_commit=False) as setup_db:
        # Get the current user
        response = client.get("/users/me", headers=test_user_token_headers)
        current_user = schemas.User(**response.json())
        
        # Create a single team session and add the user to it
        team_session_create = schemas.SessionCreate(name="The Only Team")
        team_session = crud.create_team_session(setup_db, session=team_session_create, owner_id=current_user.id)

    # 2. Mock the LLM to recognize the team context and return a session name
    mock_chain_invoke.return_value = TaskDetails(
        task_title="Review Q3 marketing results",
        session_name="The Only Team"
    )

    # 3. Call the API from the user's private context
    private_session_response = client.get("/sessions", headers=test_user_token_headers)
    private_session = next((s for s in private_session_response.json() if s.get("name") is None), None)

    request_payload = {
        "history": [{"sender": "user", "text": "Create a task for the team to review Q3 results"}],
        "current_session_id": private_session["id"] if private_session else None,
    }
    
    with TestClient(app) as client:
        response = client.post("/chat/create-task", json=request_payload, headers=test_user_token_headers)
    
    assert response.status_code == 200, response.text
    response_data = response.json()
    assert response_data["is_complete"] is True

    # 4. Verify the task was created in the correct team session
    todos = crud.get_todos_by_session(db, session_id=team_session.id, requesting_user_id=current_user.id)
    assert len(todos) == 1
    created_todo = todos[0]
    assert created_todo.title == "Review Q3 marketing results"
    assert created_todo.session_id == team_session.id

@patch("app.llm_service.ChatOpenAI")
@patch("langchain_core.runnables.base.RunnableSequence.invoke")
def test_chat_create_task_ambiguous_team_clarification(
    mock_chain_invoke: MagicMock,
    mock_chat_openai: MagicMock,
    client: TestClient,
    db: Session,
    test_user_token_headers: dict
):
    """
    Tests that the API asks for clarification when a team name is ambiguous.
    """
    # 1. Setup: Create multiple teams with similar names
    with Session(db.get_bind(), expire_on_commit=False) as setup_db:
        response = client.get("/users/me", headers=test_user_token_headers)
        current_user = schemas.User(**response.json())
        crud.create_team_session(setup_db, session=schemas.SessionCreate(name="Frontend Developers"), owner_id=current_user.id)
        crud.create_team_session(setup_db, session=schemas.SessionCreate(name="Backend Developers"), owner_id=current_user.id)

    # 2. Mock the LLM to return a clarification question
    mock_chain_invoke.return_value = TaskDetails(
        task_title="Deploy to staging",
        clarification_questions=["Which team did you mean for this task? Your teams are: 'Frontend Developers', 'Backend Developers'."]
    )

    # 3. Call the API
    request_payload = { "history": [{"sender": "user", "text": "make a task for the developers to deploy to staging"}] }
    with TestClient(app) as client:
        response = client.post("/chat/create-task", json=request_payload, headers=test_user_token_headers)
    
    assert response.status_code == 200, response.text
    response_data = response.json()
    
    # 4. Assert that the response contains the clarification and is not complete
    assert response_data["is_complete"] is False
    assert "Which team did you mean" in response_data["clarification_questions"][0]

    # 5. Assert that no task was created
    todos = crud.get_todos_by_user(db, user_id=current_user.id)
    assert len(todos) == 0

@patch("app.llm_service.ChatOpenAI")
@patch("langchain_core.runnables.base.RunnableSequence.invoke")
def test_chat_create_task_fuzzy_team_name(
    mock_chain_invoke: MagicMock,
    mock_chat_openai: MagicMock,
    client: TestClient,
    db: Session,
    test_user_token_headers: dict
):
    """
    Tests that the AI can correctly identify a team by a fuzzy name.
    """
    # 1. Setup: Create a team with a specific name
    with Session(db.get_bind(), expire_on_commit=False) as setup_db:
        response = client.get("/users/me", headers=test_user_token_headers)
        current_user = schemas.User(**response.json())
        team_session_create = schemas.SessionCreate(name="The A-Team")
        team_session = crud.create_team_session(setup_db, session=team_session_create, owner_id=current_user.id)

    # 2. Mock the LLM to return the correct session name based on a fuzzy match
    mock_chain_invoke.return_value = TaskDetails(
        task_title="Solve a problem",
        session_name="The A-Team"
    )

    # 3. Call the API with a fuzzy team name in the query
    request_payload = { "history": [{"sender": "user", "text": "I love it when a plan comes together, make a task for the A Team"}] }
    with TestClient(app) as client:
        response = client.post("/chat/create-task", json=request_payload, headers=test_user_token_headers)
    
    assert response.status_code == 200, response.text
    response_data = response.json()
    assert response_data["is_complete"] is True

    # 4. Verify the task was created in the correct team session
    todos = crud.get_todos_by_session(db, session_id=team_session.id, requesting_user_id=current_user.id)
    assert len(todos) == 1
    created_todo = todos[0]
    assert created_todo.title == "Solve a problem"
    assert created_todo.session_id == team_session.id

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
    with TestClient(app) as client:
        response = client.post(
            "/chat/create-task",
            headers=test_user_token_headers,
            json={"history": [{"sender": "user", "text": "schedule a meeting about the project"}]}
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