from typing import TypedDict, Optional, List, Literal
from datetime import date, time
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
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
    task_title: Optional[str]
    description: Optional[str]
    is_private: Optional[bool]
    is_global_public: Optional[bool]
    session_name: Optional[str]
    start_date: Optional[str]
    end_date: Optional[str]
    start_time: Optional[str]
    end_time: Optional[str]
    clarification_questions: Optional[List[str]]
    is_complete: bool

# --- Graph Nodes ---

def parse_user_request(state: TaskCreationState, config: dict):
    """Parses the user query to extract task details using the LLM."""
    user_query = state["user_query"]
    session_name = state.get("session_name") or "Private"
    team_names = state.get("team_names") or []

    # Build a string for the prompt for better readability
    team_list_str = ", ".join(f"'{name}'" for name in team_names) if team_names else "None"
    
    single_team_instructions = ""
    if len(team_names) == 1:
        single_team_instructions = f"""- The user is only in one team: '{team_names[0]}'. If the user says to create a task 'for the team' or similar without specifying a name, you MUST assume it is for this team and return `session_name: "{team_names[0]}"`."""

    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    
    system_prompt = f"""You are an expert at extracting task details for a to-do list application.
The user is currently in a workspace called '{session_name}'.
The user is a member of the following team workspaces: {team_list_str}.
Today's date is {{today}}.

From the user's request below, extract the following details:
- The task title (task_title).
- A detailed description (description).
- Start and end dates (start_date, end_date) and times (start_time, end_time).
- The user may want to create a task for a specific team. Your job is to determine the most likely team from the list of workspaces provided above. The user might not use the exact name. For example, if the user says 'for the API squad' and a team is named 'Backend API Team', you should select 'Backend API Team'. If you can confidently determine the team, you MUST extract its official name from the list as `session_name`.
{single_team_instructions}
- If you cannot confidently determine a specific team from the user's query, DO NOT return the `session_name` field.
- If the user's request implies the task is for everyone in the company or public, set `is_global_public` to true.
- If the user's request is for a personal task, set `is_private` to true. If the context is 'Private', you can assume it's private unless they specify a team.

If you don't have enough information for a `task_title`, ask clarifying questions.
- If the user's query seems to refer to a team but you are uncertain which one from the list it is, you MUST ask for clarification. Add a question like "Which team did you mean for this task? Your teams are: {team_list_str}." to the `clarification_questions` field. Do not set a `session_name` in this case.
- If the user does not mention a team at all, do not set `session_name` and do not ask for clarification about the team.
Your output MUST be a JSON object conforming to the `TaskDetails` schema.
Do not add any extra text or explanations.
"""
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
    ])
    
    chain = prompt | llm.with_structured_output(TaskDetails)
    
    try:
        details = chain.invoke({
            "user_query": user_query, 
            "today": date.today().isoformat()
        })
        return {k: v for k, v in details.model_dump().items() if v is not None}
    except Exception as e:
        return {"clarification_questions": [f"I had trouble understanding your request: {e}"]}

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