from typing import TypedDict, Optional, List, Literal
from datetime import date, time
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from sqlalchemy.orm import Session
from . import crud, schemas, models
from .database import get_db

# --- State and Tool Schemas ---

class TaskDetails(BaseModel):
    """The extracted details of a to-do task."""
    task_title: Optional[str] = Field(None, description="The title of the to-do item.")
    description: Optional[str] = Field(None, description="The detailed description of the to-do item.")
    is_private: Optional[bool] = Field(None, description="Is the to-do item private to the user? This is False if it's for a team or public.")
    is_global_public: Optional[bool] = Field(None, description="Is the task visible to everyone, regardless of team? Overrides is_private.")
    session_name: Optional[str] = Field(None, description="The name of the team or workspace this task belongs to.")
    start_date: Optional[str] = Field(None, description="The start date of the task in YYYY-MM-DD format.")
    end_date: Optional[str] = Field(None, description="The end date of the task in YYYY-MM-DD format.")
    start_time: Optional[str] = Field(None, description="The start time of the task in HH:MM:SS format.")
    end_time: Optional[str] = Field(None, description="The end time of the task in HH:MM:SS format.")
    clarification_questions: Optional[List[str]] = Field(default=None, description="Questions to ask the user if details are missing.")
    is_complete: bool = Field(default=False, description="Whether the task has been successfully created.")

class TaskCreationState(TypedDict):
    """The state of the task creation process."""
    user_query: str
    history: List[dict]
    session_name: Optional[str]
    team_names: List[str]
    task_title: Optional[str]
    description: Optional[str]
    is_private: Optional[bool]
    is_global_public: Optional[bool]
    start_date: Optional[str]
    end_date: Optional[str]
    start_time: Optional[str]
    end_time: Optional[str]
    clarification_questions: Optional[List[str]]
    is_complete: bool

# --- Graph Nodes ---

def parse_user_request(state: TaskCreationState, config: dict):
    """Parses the user query to extract task details using the LLM."""
    history = state.get("history", [])
    session_name = state.get("session_name") or "Private"
    team_names = state.get("team_names") or []

    # Build a string for the prompt for better readability
    team_list_str = ", ".join(f"'{name}'" for name in team_names) if team_names else "None"
    
    single_team_instructions = ""
    if len(team_names) == 1:
        single_team_instructions = f"""- The user is only in one team: '{team_names[0]}'. If the user says to create a task 'for the team' or similar without specifying a name, you MUST assume it is for this team and return `session_name: "{team_names[0]}"`."""

    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    
    system_prompt = f"""You are an expert assistant for a to-do list application. Your primary goal is to understand the user's request and extract the details for a task.

# Context
- The user is currently in a workspace named: '{session_name}'.
- The user is a member of the following team workspaces: {team_list_str}.
- Today's date is {{today}}.

# Instructions
1.  **Identify the Task**: First, figure out what the user wants to do. The task title is the core action or subject of the request.
    - Example 1: If the user says, "i need to call bro so make task and make it in team", the `task_title` is "Call bro".
    - Example 2: If the user says, "remind me to schedule the quarterly review", the `task_title` is "Schedule the quarterly review".
2.  **Determine the Workspace**:
    - The user may want the task in a specific team workspace. Look for team names in the user's request. The name might not be an exact match. Use the most likely team from the list provided.
    - {single_team_instructions}
    - If the user is in a team workspace and doesn't specify another, assume the task is for the current workspace by returning the current `session_name`.
    - If you are not confident about the team, ask a clarifying question.
3.  **Handle Ambiguity**:
    - If the task title is unclear, ask the user for it.
    - If the team name is unclear, ask for clarification.
    - **Crucially, if you have already asked for a detail (like the title) and the user's next message seems to provide it, you MUST accept it as the answer.**
4.  **Extract Details**: From the user's request, extract the following into a JSON object:
    - `task_title`: The title of the task.
    - `description`: Any additional details.
    - `start_date`, `end_date`, `start_time`, `end_time`: Any dates and times.
    - `session_name`: The name of the team workspace if you can confidently determine it. If it is a personal task, this should be null.
    - `is_global_public`: Set to `true` if the task is for everyone (e.g., "company-wide").
    - `is_private`: Set to `true` for personal tasks.
    - `clarification_questions`: A list of questions to ask the user if any information is missing.

Your response MUST be a JSON object matching the structure above.
"""
    
    parser = JsonOutputParser(pydantic_object=TaskDetails)

    # Convert the history to a format suitable for the prompt template
    prompt_messages = [("system", system_prompt.format(today=date.today()))]
    for msg in history:
        if msg["sender"] == "user":
            prompt_messages.append(("user", msg["text"]))
        elif msg["sender"] == "ai":
            prompt_messages.append(("ai", msg["text"]))

    prompt = ChatPromptTemplate.from_messages(prompt_messages)
    
    chain = prompt | llm | parser
    
    try:
        response_data = chain.invoke({})
    except Exception as e:
        print("--- ERROR DURING CHAIN INVOCATION ---")
        # Let's inspect the raw response
        llm_chain = prompt | llm
        raw_response_message = llm_chain.invoke({})
        print("--- RAW LLM RESPONSE (AIMessage object) ---")
        print(raw_response_message)
        print("--- RAW LLM RESPONSE CONTENT ---")
        print(raw_response_message.content)
        print("--- CHAIN INVOCATION FAILED WITH ---")
        print(e)
        print("--- END ERROR INFO ---")
        raise e

    # Update state with the extracted details
    updated_state = state.copy()
    llm_output = response_data.model_dump(exclude_unset=True)
    
    # Preserve original session_name for implicit team tasks
    if llm_output.get('session_name') is None and not llm_output.get('is_private'):
        llm_output.pop('session_name', None)

    updated_state.update(llm_output)

    # The 'user_query' is now the full history context, but we can keep the last message
    # for logging or simple branching if needed.
    if history:
        updated_state["user_query"] = history[-1]["text"]

    return updated_state

def should_continue(state: TaskCreationState) -> Literal["task_creator", "clarification_requester"]:
    """Determines the next step based on whether a task title was extracted."""
    title = state.get("task_title")
    if not isinstance(title, str) or not title:
        return "clarification_requester"
    return "task_creator"

def create_task_in_db(state: TaskCreationState, config: dict):
    """Creates a new task in the database based on the extracted details."""
    # If there are clarification questions, we should not create a task.
    if state.get("clarification_questions"):
        return { "is_complete": False }

    db: Session = config["configurable"]["db_session"]
    owner_id: int = config["configurable"]["owner_id"]
    title = state.get("task_title")

    if not title:
        # This should have been caught by the clarification branch, but as a safeguard.
        return { "is_complete": False, "clarification_questions": ["What is the title of the task?"] }

    try:
        session_id = None
        session_name = state.get("session_name")
        if session_name:
            # Note: A proper implementation would use a robust CRUD function.
            # This direct query is for simplicity in this context.
            session_obj = db.query(models.Session).filter(models.Session.name == session_name).first()
            if session_obj:
                # Further check if user is a member of this session
                member_check = db.query(models.SessionMember).filter(
                    models.SessionMember.session_id == session_obj.id,
                    models.SessionMember.user_id == owner_id
                ).first()
                if member_check:
                    session_id = session_obj.id
        
        def parse_date(date_str: Optional[str]) -> Optional[date]:
            return date.fromisoformat(date_str) if isinstance(date_str, str) else None

        def parse_time(time_str: Optional[str]) -> Optional[time]:
            return time.fromisoformat(time_str) if isinstance(time_str, str) else None

        todo_create = schemas.TodoCreate(
            title=title,
            description=state.get("description"),
            is_private=state.get("is_private"),
            is_global_public=state.get("is_global_public"),
            session_id=session_id,
            start_date=parse_date(state.get("start_date")),
            end_date=parse_date(state.get("end_date")),
            start_time=parse_time(state.get("start_time")),
            end_time=parse_time(state.get("end_time")),
        )
        
        crud.create_todo(db=db, todo=todo_create, owner_id=owner_id)
        return {"is_complete": True}

    except Exception as e:
        return {"is_complete": False, "clarification_questions": [f"An internal error occurred: {e}"]}

def request_clarification(state: TaskCreationState, config: dict):
    """Handles cases where more information is needed."""
    return {"is_complete": False, "clarification_questions": ["I'm sorry, I couldn't determine a task title. What is the task?"]}


# --- Graph Definition ---
def create_graph():
    """Creates and returns the LangGraph for task creation."""
    graph = StateGraph(TaskCreationState)
    graph.add_node("parser", parse_user_request)
    graph.add_node("task_creator", create_task_in_db)
    graph.add_node("clarification_requester", request_clarification)
    graph.add_conditional_edges(
        "parser",
        should_continue,
        {"task_creator": "task_creator", "clarification_requester": "clarification_requester"}
    )
    graph.add_edge("task_creator", END)
    graph.add_edge("clarification_requester", END)
    graph.set_entry_point("parser")
    return graph.compile() 