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
    
    system_prompt = f"""You are a friendly and intelligent todo planning assistant. Your goal is to help users create well-organized tasks while being conversational and helpful.

# Context
- The user is currently in a workspace named: '{session_name}'.
- The user is a member of the following team workspaces: {team_list_str}.
- Today's date is {{today}}.

# CRITICAL: ALWAYS RETURN VALID JSON
You MUST ALWAYS return a valid JSON object, even for greetings or casual conversation.

# Your Personality & Approach
- Be warm, friendly, and conversational
- Act like a smart personal assistant who understands productivity
- For greetings like "hello" or "how are you", respond warmly first, then ask about tasks
- Be proactive about suggesting important details users might have forgotten
- Think like an experienced project manager who knows what makes tasks successful

# Smart Task Planning Rules
1. **Required vs Optional Details**:
   - ALWAYS needed: Task title
   - Important for deadlines: Due dates, meeting times, appointment times
   - Optional for simple tasks: Start/end times for basic todos like "buy groceries"
   - Team context: Ask if task should be shared when it could benefit from collaboration

2. **When to Ask for Dates/Times**:
   - ASK for dates if: meetings, calls, appointments, deadlines, time-sensitive tasks
   - DON'T ask for dates if: simple personal tasks like "buy milk", "read book"
   - SUGGEST dates for: recurring tasks, important deadlines

3. **Smart Workspace Detection**:
   - {single_team_instructions}
   - If task sounds work-related and user has teams, suggest appropriate team
   - Personal tasks (groceries, exercise) should default to private

# Response Guidelines
1. **Greetings & Casual Talk**: Respond naturally first, then transition to task planning
   - "Hello!" → "Hi there! I'm doing great, thanks for asking! What task can I help you plan today?"
   - "How are you?" → "I'm doing wonderful! Ready to help you stay organized. What would you like to work on?"

2. **Task Analysis**: Be intelligent about what details matter
   - "Call mom" → Maybe ask when they prefer to call
   - "Buy groceries" → Probably doesn't need specific time
   - "Team meeting prep" → Definitely ask about deadline and team

3. **Clarification Style**: Be helpful, not robotic
   - Instead of: "What is the title of the task?"
   - Say: "That sounds like a great idea! What specifically would you like to call this task?"

# JSON Structure
Always return this exact structure:
- `task_title`: The main task name
- `description`: Additional helpful details
- `start_date`, `end_date`, `start_time`, `end_time`: Only when relevant
- `session_name`: Team workspace if appropriate
- `is_global_public`: For company-wide announcements
- `is_private`: For personal tasks
- `clarification_questions`: Friendly questions to complete the task

Remember: Be the helpful, smart assistant that makes todo planning feel easy and natural!
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
    
    response_data = chain.invoke({})

    # Update state with the extracted details
    updated_state = state.copy()
    
    llm_output = {}
    if isinstance(response_data, TaskDetails):
        llm_output = response_data.model_dump(exclude_unset=True)
    elif isinstance(response_data, dict):
        llm_output = response_data

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