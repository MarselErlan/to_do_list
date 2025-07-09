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
    """Parses task creation requests with an enhanced intelligent prompt."""
    history = state.get("history", [])
    session_name = state.get("session_name") or "Private"
    team_names = state.get("team_names") or []
    
    team_list_str = ", ".join(f"'{name}'" for name in team_names) if team_names else "None"
    
    single_team_instructions = ""
    if len(team_names) == 1:
        single_team_instructions = f"- The user is only in one team: '{team_names[0]}'. If the user says to create a task 'for the team' or similar without specifying a name, you MUST assume it is for this team and return session_name: {team_names[0]}."

    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    
    # Enhanced intelligent system prompt - template-free but smart
    system_prompt = f"""You are an intelligent task planning assistant. Your job is to understand user intent and extract task details to return ONLY valid JSON.

CONTEXT:
- Current workspace: {session_name}
- Available teams: {team_list_str}
- Current date and time: {date.today()}

INTELLIGENCE REQUIREMENTS:

1. TIME PARSING EXPERTISE:
   - "after 1 hour" -> set start_date to today (YYYY-MM-DD) AND start_time as current time + 1 hour (HH:MM:SS)
   - "in 15 minutes" -> set start_date to today (YYYY-MM-DD) AND start_time as current time + 15 minutes (HH:MM:SS)
   - "tomorrow morning" -> set start_date to tomorrow (YYYY-MM-DD), start_time to 09:00:00
   - "next week" -> set start_date to next Monday (YYYY-MM-DD format)
   - "at 3pm" -> set start_date to today (YYYY-MM-DD) AND start_time to 15:00:00 (HH:MM:SS format)
   - CRITICAL: Always use separate date and time fields, NEVER combine them
   - CRITICAL: For relative times (after/in X minutes/hours), ALWAYS set today's date too

2. TASK TITLE EXTRACTION:
   - "call Ruslan after 1 hour" -> task_title: "Call Ruslan"
   - "remind me to buy groceries" -> task_title: "Buy groceries"  
   - "schedule meeting with team" -> task_title: "Meeting with team"
   - Extract the core action, not the timing instruction

3. CONTEXT UNDERSTANDING:
   - Personal tasks (groceries, personal calls) -> is_private: true
   - Work tasks with teams available -> suggest appropriate team
   - Time-sensitive requests -> ALWAYS set appropriate time fields
   - Casual conversation -> return clarification_questions with friendly response

4. SMART PROCESSING:
   {single_team_instructions}
   - If user says "hello" or greetings, respond warmly but ask what task they need
   - If task details are clear, extract them intelligently
   - If ambiguous, ask specific clarifying questions

CRITICAL OUTPUT REQUIREMENTS:
- Return ONLY valid JSON object
- NO text before or after JSON
- NO comments in JSON
- NO conversational text outside JSON structure

JSON FIELDS TO POPULATE:
- task_title: The main action/task (required for task creation)
- description: Additional details if provided
- start_date: YYYY-MM-DD format ONLY (e.g., "2025-01-15")
- end_date: YYYY-MM-DD format ONLY if end date mentioned  
- start_time: HH:MM:SS format ONLY (e.g., "14:30:00")
- end_time: HH:MM:SS format ONLY if duration/end time mentioned
- session_name: team name if work-related or specified
- is_private: true for personal tasks, false for team tasks
- is_global_public: true only if explicitly company-wide
- clarification_questions: array of specific questions if info missing
- is_complete: false (always false, system will set true when task created)

EXAMPLES OF INTELLIGENT PROCESSING:
- Input: "call Ruslan after 1 hour"
  Smart processing: Extract "Call Ruslan" as title, set start_date to today, calculate start_time as now + 1 hour in HH:MM:SS format
  
- Input: "remind me to buy groceries tomorrow at 10am"  
  Smart processing: Extract "Buy groceries" as title, set start_date to tomorrow in YYYY-MM-DD, start_time to "10:00:00"

- Input: "schedule team meeting next week"
  Smart processing: Extract "Team meeting" as title, set start_date to next Monday in YYYY-MM-DD format

- Input: "call client at 3pm"
  Smart processing: Extract "Call client" as title, set start_date to today, set start_time to "15:00:00"

CRITICAL: NEVER use combined datetime formats like "2025-01-15T14:30:00". Always use separate date and time fields.

Be intelligent, contextual, and user-friendly while maintaining strict JSON output format."""

    parser = JsonOutputParser(pydantic_object=TaskDetails)
    
    # Build conversation context without any template variables
    messages = []
    messages.append(("system", system_prompt))
    
    for msg in history:
        if msg["sender"] == "user":
            messages.append(("user", msg["text"]))
        elif msg["sender"] == "ai":
            messages.append(("ai", msg["text"]))

    # Use direct prompt creation to avoid template processing
    prompt = ChatPromptTemplate.from_messages(messages)
    chain = prompt | llm | parser
    
    try:
        response_data = chain.invoke({})
    except Exception as e:
        # Fallback if chain fails
        return {
            "is_complete": False,
            "clarification_questions": ["I encountered an error processing your request. Could you please rephrase your task?"],
            "user_query": history[-1]["text"] if history else ""
        }

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

    # Smart fallback: if start_time is set but start_date is missing, assume today
    if llm_output.get('start_time') and not llm_output.get('start_date'):
        llm_output['start_date'] = date.today().isoformat()

    updated_state.update(llm_output)

    # Set user query for logging
    if history:
        updated_state["user_query"] = history[-1]["text"]

    return updated_state

def route_from_router(state: TaskCreationState) -> Literal["conversation", "task_parser"]:
    """Routes from router based on input type."""
    if state.get("is_conversation"):
        return "conversation"
    return "task_parser"

def route_from_task_parser(state: TaskCreationState) -> Literal["task_creator", "clarification_requester"]:
    """Routes from task parser based on task completeness."""
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
            """Parse date string with robust error handling."""
            if not isinstance(date_str, str):
                return None
            try:
                # Handle ISO datetime format (extract date part)
                if 'T' in date_str:
                    date_str = date_str.split('T')[0]
                return date.fromisoformat(date_str)
            except (ValueError, TypeError):
                return None

        def parse_time(time_str: Optional[str]) -> Optional[time]:
            """Parse time string with robust error handling."""
            if not isinstance(time_str, str):
                return None
            try:
                # Handle ISO datetime format (extract time part)
                if 'T' in time_str:
                    time_str = time_str.split('T')[1]
                # Remove timezone info if present
                if '+' in time_str:
                    time_str = time_str.split('+')[0]
                if 'Z' in time_str:
                    time_str = time_str.replace('Z', '')
                # Ensure format is HH:MM:SS
                if len(time_str.split(':')) == 2:
                    time_str += ':00'
                return time.fromisoformat(time_str)
            except (ValueError, TypeError):
                return None

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
    
    # Router routes to either conversation or task_parser
    graph.add_conditional_edges(
        "router",
        route_from_router,
        {
            "conversation": "conversation",
            "task_parser": "task_parser"
        }
    )
    
    # Conversation goes directly to end (returns clarification_questions)
    graph.add_edge("conversation", "clarification_requester")
    
    # Task parser routes to either task creation or clarification
    graph.add_conditional_edges(
        "task_parser",
        route_from_task_parser,
        {
            "task_creator": "task_creator",
            "clarification_requester": "clarification_requester"
        }
    )
    
    # Terminal nodes
    graph.add_edge("task_creator", END)
    graph.add_edge("clarification_requester", END)
    
    return graph.compile() 