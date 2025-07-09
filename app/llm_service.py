from typing import List, Optional, Literal, TypedDict
from datetime import date, time
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END
from sqlalchemy.orm import Session
from app import models, schemas, crud

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

class ConversationResponse(BaseModel):
    """Response for casual conversation and greetings."""
    response_type: str = Field(default="conversation", description="Type of response (conversation/greeting)")
    message: str = Field(description="Friendly conversational response")
    follow_up: Optional[str] = Field(None, description="Optional follow-up question about tasks")

class TaskCreationState(TypedDict):
    """The state of the task creation process."""
    user_query: str
    history: List[dict]
    session_name: Optional[str]
    team_names: List[str]
    
    # Routing
    is_conversation: Optional[bool]
    conversation_response: Optional[str]
    
    # Task fields
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

def route_input(state: TaskCreationState, config: dict):
    """Routes input to either conversation or task creation based on content."""
    history = state.get("history", [])
    if not history:
        return {"is_conversation": False}
    
    last_message = history[-1]["text"].lower().strip()
    
    # Simple greeting detection
    greetings = ["hello", "hi", "hey", "good morning", "good afternoon", "good evening", 
                "how are you", "what's up", "whats up", "sup"]
    
    # Check if it's a greeting
    is_greeting = any(greeting in last_message for greeting in greetings)
    
    # Check if it's a short casual message without task indicators
    task_indicators = ["create", "task", "todo", "remind", "schedule", "meeting", "call", 
                      "buy", "do", "finish", "complete", "work on"]
    has_task_indicators = any(indicator in last_message for indicator in task_indicators)
    
    # If it's a greeting or short message without task indicators, treat as conversation
    is_conversation = is_greeting or (len(last_message.split()) <= 3 and not has_task_indicators)
    
    return {"is_conversation": is_conversation}

def handle_conversation(state: TaskCreationState, config: dict):
    """Handles greetings and casual conversation."""
    history = state.get("history", [])
    if not history:
        return {"conversation_response": "Hello! How can I help you create a task today?"}
    
    last_message = history[-1]["text"].lower().strip()
    
    # Mirror greetings and provide friendly responses
    if "hello" in last_message:
        response = "Hello! Hi there! I'm doing great, thanks for asking! What task can I help you plan today?"
    elif "hi" in last_message:
        response = "Hi! Hello there! Great to see you! What would you like to work on today?"
    elif "hey" in last_message:
        response = "Hey there! Hello! How can I help you create an awesome task today?"
    elif "how are you" in last_message:
        response = "I'm doing wonderful! Thanks for asking! Ready to help you stay organized. What would you like to work on?"
    elif "good morning" in last_message:
        response = "Good morning! Hope you're having a great start to your day! What would you like to accomplish?"
    else:
        response = "Hello! I'm here to help you create and organize tasks. What would you like to work on?"
    
    return {
        "conversation_response": response,
        "clarification_questions": [response],
        "is_complete": False
    }

def parse_task_request(state: TaskCreationState, config: dict):
    """Parses task creation requests with a clean, focused prompt."""
    history = state.get("history", [])
    session_name = state.get("session_name") or "Private"
    team_names = state.get("team_names") or []
    
    team_list_str = ", ".join(f"'{name}'" for name in team_names) if team_names else "None"
    
    single_team_instructions = ""
    if len(team_names) == 1:
        single_team_instructions = f"- The user is only in one team: '{team_names[0]}'. If the user says to create a task 'for the team' or similar without specifying a name, you MUST assume it is for this team and return `session_name: \"{team_names[0]}\"`."

    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    
    system_prompt = f"""You are a task planning assistant. Extract task details from user input and return ONLY valid JSON.

# Context
- Current workspace: '{session_name}'
- Available teams: {team_list_str}
- Today's date: {{today}}

# CRITICAL: JSON-ONLY OUTPUT
- Return ONLY a valid JSON object
- NO text before or after JSON
- NO comments in JSON
- NO conversational text outside JSON structure

# Task Analysis Rules
1. **Required**: task_title (always needed)
2. **Important for scheduling**: start_date, end_date, start_time, end_time
3. **Team detection**: {single_team_instructions}
4. **Privacy**: is_private (true for personal tasks), is_global_public (company-wide)

# Smart Defaults
- Personal tasks (groceries, exercise) → is_private: true
- Work tasks with teams available → suggest appropriate team
- Time-sensitive tasks → ask for dates/times
- Simple todos → minimal fields needed

# Output Structure
{{
  "task_title": "string or null",
  "description": "string or null", 
  "start_date": "YYYY-MM-DD or null",
  "end_date": "YYYY-MM-DD or null",
  "start_time": "HH:MM:SS or null",
  "end_time": "HH:MM:SS or null",
  "session_name": "team name or null",
  "is_private": "boolean or null",
  "is_global_public": "boolean or null",
  "clarification_questions": ["array of questions if needed"],
  "is_complete": false
}}

Remember: Extract what you can, ask clarification for missing critical details only."""

    parser = JsonOutputParser(pydantic_object=TaskDetails)
    
    # Build conversation context
    prompt_messages = [("system", system_prompt.format(today=date.today()))]
    for msg in history:
        if msg["sender"] == "user":
            prompt_messages.append(("user", msg["text"]))
        elif msg["sender"] == "ai":
            prompt_messages.append(("ai", msg["text"]))

    prompt = ChatPromptTemplate.from_messages(prompt_messages)
    chain = prompt | llm | parser
    
    response_data = chain.invoke({})

    # Update state with extracted details
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

    # Set user query for logging
    if history:
        updated_state["user_query"] = history[-1]["text"]

    return updated_state

def should_continue(state: TaskCreationState) -> Literal["conversation", "task_parser", "task_creator", "clarification_requester"]:
    """Routes to appropriate node based on input type and task completeness."""
    # First check if it's conversation
    if state.get("is_conversation"):
        return "conversation"
    
    # If we have a conversation response, we're done
    if state.get("conversation_response"):
        return "clarification_requester"
    
    # Check if we have enough info to create a task
    title = state.get("task_title")
    if not isinstance(title, str) or not title:
        return "clarification_requester"
    
    return "task_creator"

def create_task_in_db(state: TaskCreationState, config: dict):
    """Creates a new task in the database based on the extracted details."""
    # If there are clarification questions, we should not create a task
    if state.get("clarification_questions"):
        return {"is_complete": False}

    db: Session = config["configurable"]["db_session"]
    owner_id: int = config["configurable"]["owner_id"]
    title = state.get("task_title")

    if not title:
        return {"is_complete": False, "clarification_questions": ["What is the title of the task?"]}

    try:
        session_id = None
        session_name = state.get("session_name")
        if session_name:
            session_obj = db.query(models.Session).filter(models.Session.name == session_name).first()
            if session_obj:
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
    # If we have a conversation response, return it
    if state.get("conversation_response"):
        return {"is_complete": False}
    
    # Otherwise, ask for task clarification
    return {"is_complete": False, "clarification_questions": ["I'm sorry, I couldn't determine a task title. What is the task?"]}

# --- Graph Definition ---
def create_graph():
    """Creates and returns the LangGraph for task creation with conversation handling."""
    graph = StateGraph(TaskCreationState)
    
    # Add nodes
    graph.add_node("router", route_input)
    graph.add_node("conversation", handle_conversation)
    graph.add_node("task_parser", parse_task_request)
    graph.add_node("task_creator", create_task_in_db)
    graph.add_node("clarification_requester", request_clarification)
    
    # Set entry point
    graph.set_entry_point("router")
    
    # Add conditional edges from router
    graph.add_conditional_edges(
        "router",
        should_continue,
        {
            "conversation": "conversation",
            "task_parser": "task_parser", 
            "task_creator": "task_creator",
            "clarification_requester": "clarification_requester"
        }
    )
    
    # Add edges from conversation and task_parser to conditional router
    graph.add_conditional_edges(
        "conversation", 
        should_continue,
        {
            "conversation": "conversation",
            "task_parser": "task_parser",
            "task_creator": "task_creator", 
            "clarification_requester": "clarification_requester"
        }
    )
    
    graph.add_conditional_edges(
        "task_parser",
        should_continue,
        {
            "conversation": "conversation",
            "task_parser": "task_parser",
            "task_creator": "task_creator",
            "clarification_requester": "clarification_requester"
        }
    )
    
    # Terminal nodes
    graph.add_edge("task_creator", END)
    graph.add_edge("clarification_requester", END)
    
    return graph.compile() 