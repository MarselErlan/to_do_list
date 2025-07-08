import pytest
from unittest.mock import MagicMock
from app.llm_service import create_graph
from app import schemas, crud

# This test is now complete.
def test_graph_creation(monkeypatch):
    """
    Test that the LangGraph graph is created successfully, mocking the LLM.
    """
    # Use monkeypatch to replace the real ChatOpenAI with our mock
    monkeypatch.setattr("app.llm_service.ChatOpenAI", MagicMock())

    # Call the function that creates the graph
    graph = create_graph()

    # Assert that the graph and its components are created
    assert graph is not None
    assert "parser" in graph.nodes
    assert "task_creator" in graph.nodes


def test_task_creator_node(monkeypatch):
    """
    Tests that the create_task_in_db function correctly calls crud.create_todo.
    """
    # 1. Mock the dependencies
    mock_db_session = MagicMock()
    # Mock the query chain for finding a session
    mock_query = MagicMock()
    mock_db_session.query.return_value.filter.return_value.first.return_value = MagicMock(id=123)
    mock_create_todo = MagicMock()
    monkeypatch.setattr(crud, "create_todo", mock_create_todo)

    # 2. Define the input state and config for the function
    input_state = {
        "task_title": "Finalize report", "description": "Compile all data.",
        "is_private": False, "is_global_public": False,
        "session_name": "Project X", "start_date": "2024-10-27",
        "end_date": "2024-10-28", "start_time": "09:00:00",
        "end_time": "17:00:00"
    }
    config = {
        "configurable": {
            "db_session": mock_db_session,
            "owner_id": 1
        }
    }

    # 3. Call the function directly
    from app.llm_service import create_task_in_db
    result = create_task_in_db(input_state, config)

    # 4. Assert that crud.create_todo was called correctly
    mock_create_todo.assert_called_once()
    
    args, kwargs = mock_create_todo.call_args
    assert kwargs["db"] == mock_db_session
    assert kwargs["owner_id"] == 1
    
    created_todo = kwargs["todo"]
    assert isinstance(created_todo, schemas.TodoCreate)
    assert created_todo.title == "Finalize report"
    assert created_todo.session_id == 123
    
    # 5. Assert the function returns the correct state update
    assert result == {"is_complete": True} 

def test_clarification_loop(monkeypatch):
    """
    Tests that the graph enters the clarification loop if the title is missing.
    """
    # 1. Mock the parser to return an incomplete state (no title)
    parser_output = {"task_title": None, "description": "A meeting about the project"}
    monkeypatch.setattr("app.llm_service.parse_user_request", lambda state, config: parser_output)

    # 2. Mock the clarification node to see if it's called
    clarification_output = {"clarification_questions": ["What is the title of the task?"]}
    mock_clarification_node = MagicMock(return_value=clarification_output)
    monkeypatch.setattr("app.llm_service.request_clarification", mock_clarification_node)

    # 3. We must also mock crud.create_todo to ensure it is NOT called
    mock_create_todo = MagicMock()
    monkeypatch.setattr(crud, "create_todo", mock_create_todo)
    
    # 4. Mock the LLM instantiation
    monkeypatch.setattr("app.llm_service.ChatOpenAI", MagicMock())

    # 5. Create the graph and invoke it
    graph = create_graph()
    final_state = graph.invoke({"user_query": "a meeting about the project", "clarification_questions": [], "is_complete": False})

    # 6. Assertions
    mock_clarification_node.assert_called_once()
    mock_create_todo.assert_not_called()
    assert final_state["clarification_questions"] == ["What is the title of the task?"]
    assert final_state.get("is_complete") is not True 

def test_prompt_with_session_context(monkeypatch):
    """
    Tests that the prompt correctly includes the session name from the state.
    """
    # 1. Mock the LLM and the prompt template to inspect them
    mock_llm = MagicMock()
    # Make the ChatOpenAI return our mock LLM
    mock_chat_openai_class = MagicMock()
    mock_chat_openai_class.return_value = mock_llm
    monkeypatch.setattr("app.llm_service.ChatOpenAI", mock_chat_openai_class)
    
    # Correctly mock the class method `from_messages`
    mock_from_messages = MagicMock()
    monkeypatch.setattr("app.llm_service.ChatPromptTemplate.from_messages", mock_from_messages)
    
    # 2. Define the input state with a session name
    input_state = {
        "user_query": "Create a task for the design review",
        "session_name": "Frontend Team Workspace",
        "history": [{"sender": "user", "text": "Create a task for the design review"}],
        "team_names": [],
        "task_title": None, "description": None, "is_private": False,
        "is_global_public": False, "start_date": None, "end_date": None,
        "start_time": None, "end_time": None, "clarification_questions": [],
        "is_complete": False
    }
    
    # 3. Call the function
    from app.llm_service import parse_user_request
    parse_user_request(input_state, {})

    # 4. Assert that the prompt contains the session name
    # The first call to from_messages has the prompt content
    args, kwargs = mock_from_messages.call_args
    # The prompt is now a single system message: [('system', prompt_string)]
    system_message_content = args[0][0][1]
    
    assert "Frontend Team Workspace" in system_message_content
    assert "The user is currently in a workspace named: 'Frontend Team Workspace'" in system_message_content

def test_prompt_with_multiple_teams(monkeypatch):
    """
    Tests that the prompt correctly includes a list of multiple team names.
    """
    mock_llm = MagicMock()
    mock_chat_openai_class = MagicMock()
    mock_chat_openai_class.return_value = mock_llm
    monkeypatch.setattr("app.llm_service.ChatOpenAI", mock_chat_openai_class)
    
    mock_from_messages = MagicMock()
    monkeypatch.setattr("app.llm_service.ChatPromptTemplate.from_messages", mock_from_messages)
    
    input_state = {
        "user_query": "Create a task for the backend team",
        "session_name": "Private",
        "history": [{"sender": "user", "text": "Create a task for the backend team"}],
        "team_names": ["Frontend Team", "Backend Team", "Design Team"],
        "task_title": None, "description": None, "is_private": False,
        "is_global_public": False, "start_date": None, "end_date": None,
        "start_time": None, "end_time": None, "clarification_questions": [],
        "is_complete": False
    }
    
    from app.llm_service import parse_user_request
    parse_user_request(input_state, {})

    args, kwargs = mock_from_messages.call_args
    system_message_content = args[0][0][1]
    
    assert "The user is a member of the following team workspaces: 'Frontend Team', 'Backend Team', 'Design Team'" in system_message_content

def test_prompt_with_single_team_context(monkeypatch):
    """
    Tests that the prompt includes the special instruction when the user is in only one team.
    """
    mock_llm = MagicMock()
    mock_chat_openai_class = MagicMock()
    mock_chat_openai_class.return_value = mock_llm
    monkeypatch.setattr("app.llm_service.ChatOpenAI", mock_chat_openai_class)
    
    mock_from_messages = MagicMock()
    monkeypatch.setattr("app.llm_service.ChatPromptTemplate.from_messages", mock_from_messages)
    
    input_state = {
        "user_query": "Create a task for the team",
        "session_name": "Private",
        "history": [{"sender": "user", "text": "Create a task for the team"}],
        "team_names": ["Marketing Team"],
        "task_title": None, "description": None, "is_private": False,
        "is_global_public": False, "start_date": None, "end_date": None,
        "start_time": None, "end_time": None, "clarification_questions": [],
        "is_complete": False
    }
    
    from app.llm_service import parse_user_request
    parse_user_request(input_state, {})

    args, kwargs = mock_from_messages.call_args
    system_message_content = args[0][0][1]
    
    expected_instruction = "If you are not confident about the team, ask a clarifying question."
    assert expected_instruction in system_message_content

def test_prompt_with_ambiguous_team_clarification(monkeypatch):
    """
    Tests that the prompt includes instructions to clarify when the team is ambiguous.
    """
    mock_llm = MagicMock()
    mock_chat_openai_class = MagicMock()
    mock_chat_openai_class.return_value = mock_llm
    monkeypatch.setattr("app.llm_service.ChatOpenAI", mock_chat_openai_class)
    
    mock_from_messages = MagicMock()
    monkeypatch.setattr("app.llm_service.ChatPromptTemplate.from_messages", mock_from_messages)
    
    input_state = {
        "user_query": "A task for the dev team",
        "session_name": "Private",
        "history": [{"sender": "user", "text": "A task for the dev team"}],
        "team_names": ["Frontend Dev Team", "Backend Dev Team"],
        "task_title": None, "description": None, "is_private": False,
        "is_global_public": False, "start_date": None, "end_date": None,
        "start_time": None, "end_time": None, "clarification_questions": [],
        "is_complete": False
    }
    
    from app.llm_service import parse_user_request
    parse_user_request(input_state, {})

    args, kwargs = mock_from_messages.call_args
    system_message_content = args[0][0][1]
    
    expected_instruction = "If you are not confident about the team, ask a clarifying question."
    assert expected_instruction in system_message_content
    # This next line is the one that was missing
    assert "The user is a member of the following team workspaces: 'Frontend Dev Team', 'Backend Dev Team'" in system_message_content


# --- TDD Test for JSON Output Failure ---

# To run this test:
# 1. Make sure you have a .env file in the root of the project.
# 2. Add the following environment variables to your .env file:
#    OPENAI_API_KEY="your_openai_api_key"
#    LANGCHAIN_TRACING_V2="true"
#    LANGCHAIN_API_KEY="your_langsmith_api_key"
#    LANGCHAIN_PROJECT="your_project_name"  # e.g., "ToDo-App-TDD"
#
# This test is designed to be a temporary, focused integration test to diagnose
# the JSON parsing issue. It makes a real call to the OpenAI API.
#
@pytest.mark.integration
def test_llm_json_output_failure():
    """
    TDD Integration Test: Verifies the LLM call and JSON parsing.
    This test will fail if the LLM output is not valid JSON, helping us
    debug the `JSONDecodeError` with LangSmith tracing enabled.
    """
    from app.llm_service import parse_user_request
    from app.config import settings
    
    # Ensure the required environment variables are loaded for the test
    # The test will fail if the OPENAI_API_KEY is not set, which is expected.
    assert settings.OPENAI_API_KEY, "OPENAI_API_KEY must be set in your .env file for this test."
    
    # 1. Define a realistic input state that might cause issues
    input_state = {
        "history": [{"sender": "user", "text": "I need to prepare for the quarterly review meeting"}],
        "user_query": "I need to prepare for the quarterly review meeting",
        "session_name": "Private",
        "team_names": ["Engineering", "Product"],
        "task_title": None,
        "description": None,
        "is_private": None,
        "is_global_public": None,
        "start_date": None,
        "end_date": None,
        "start_time": None,
        "end_time": None,
        "clarification_questions": None,
        "is_complete": False,
    }

    # 2. Define a minimal config (no database needed for this parser test)
    config = {}

    # 3. Call the function
    # This call will be traced by LangSmith if the environment variables are set.
    try:
        result_state = parse_user_request(input_state, config)
        
        # 4. Assertions: Check if the parsing was successful and returned data
        assert result_state is not None
        assert isinstance(result_state, dict)
        assert result_state.get("task_title") is not None, "The LLM failed to extract a task title."
        print("LLM Output:", result_state)

    except Exception as e:
        pytest.fail(f"The 'parse_user_request' function failed with an unexpected exception: {e}")