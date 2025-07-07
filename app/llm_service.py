from typing import TypedDict, Optional, List, Literal
from datetime import date, time
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from sqlalchemy.orm import Session
from . import crud, schemas, models

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
    clarification_questions: List[str]
    is_complete: bool

# --- Graph Nodes ---

def parse_user_request(state: TaskCreationState, config: dict):
    """Parses the user query to extract task details using the LLM."""
    user_query = state["user_query"]
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an expert at extracting task details for a to-do list application from a user's query. "
                   "Today's date is {today}. Extract all relevant fields from the user's request. "
                   "If a workspace or team name is mentioned, extract it as session_name. "
                   "If the user says something is for 'everyone' or 'public', set is_global_public to True."),
        ("human", "{user_query}")
    ])
    
    chain = prompt | llm.with_structured_output(TaskDetails)
    
    try:
        details = chain.invoke({"user_query": user_query, "today": date.today().isoformat()})
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
    db: Session = config["configurable"]["db_session"]
    owner_id: int = config["configurable"]["owner_id"]
    title = state.get("task_title")

    if not title:
        return {"is_complete": False, "clarification_questions": ["The task title is missing."]}

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