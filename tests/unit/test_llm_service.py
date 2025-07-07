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
    mock_create_todo = MagicMock()
    monkeypatch.setattr(crud, "create_todo", mock_create_todo)

    mock_get_session_by_name = MagicMock(return_value=MagicMock(id=123))
    monkeypatch.setattr("app.llm_service.get_session_by_name", mock_get_session_by_name)

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
    monkeypatch.setattr("app.llm_service.parse_user_request", lambda state, llm: parser_output)

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
    final_state = graph.invoke({"user_query": "a meeting about the project"})

    # 6. Assertions
    mock_clarification_node.assert_called_once()
    mock_create_todo.assert_not_called()
    assert final_state["clarification_questions"] == ["What is the title of the task?"]
    assert final_state.get("is_complete") is not True 