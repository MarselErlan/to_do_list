from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, status, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
import os
from datetime import date, datetime, timedelta
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.routing import APIRoute
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from jose import JWTError, jwt
from contextlib import asynccontextmanager

from . import crud, models, schemas, llm_service
from .database import SessionLocal, engine, get_db, init_db
from .security import create_access_token, verify_password, get_password_hash
from .config import settings
from .email import send_verification_email
from .voice_assistant import VoiceAssistant

# Global variable to hold the graph instance
task_creation_graph = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Initializes the LangGraph instance when the application starts.
    """
    global task_creation_graph
    # This creates the graph with the actual OpenAI LLM
    task_creation_graph = llm_service.create_graph()
    print("--- Task Creation Graph Initialized (via lifespan) ---")
    yield
    # Clean up resources if needed on shutdown
    task_creation_graph = None
    print("--- Task Creation Graph De-initialized (via lifespan) ---")

# Initialize database tables
init_db()

app = FastAPI(
    title="Todo List API",
    description="A simple todo list API built with FastAPI",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://v0-recreate-ui-from-s-git-9b108d-ethanabduraimov-7965s-projects.vercel.app",
        "https://mtodo.online"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = schemas.TokenData(username=username)
    except JWTError:
        raise credentials_exception
    
    user = crud.get_user_by_username(db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user

# --- Chat Endpoint ---

@app.post("/chat/create-task")
def chat_create_task(
    request: schemas.ChatRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Handles a conversational request to create a to-do task.
    ALWAYS returns valid JSON to prevent CORS errors.
    """
    if not task_creation_graph:
        raise HTTPException(status_code=500, detail="Graph not initialized")

    try:
        session_name = "Private" # Default to private
        if request.current_session_id:
            session = crud.get_session_by_id_for_user(db, session_id=request.current_session_id, user_id=current_user.id)
            if session and session.name:
                session_name = session.name

        # Get all team names for the user to provide as context to the LLM
        all_sessions = crud.get_sessions_for_user(db, user_id=current_user.id)
        team_names = [s.name for s in all_sessions if s.name]

        # The user's most recent message is the primary query for this turn.
        user_query = ""
        if request.history:
            last_message = request.history[-1]
            if last_message.sender == 'user':
                user_query = last_message.text

        # Initial state for the graph, ensuring all necessary fields are present
        initial_state = {
            "user_query": user_query,
            "history": [msg.model_dump() for msg in request.history],
            "session_name": session_name,
            "team_names": team_names,
            "task_title": None,
            "description": None,
            "start_date": None,
            "end_date": None,
            "start_time": None,
            "end_time": None,
            "is_complete": False,
            "clarification_questions": [],
        }
        
        # Configuration to pass to the graph
        config = {
            "configurable": {
                "db_session": db,
                "owner_id": current_user.id
            }
        }

        # Invoke the graph and return the final state
        final_state = task_creation_graph.invoke(initial_state, config=config)
        
        # Ensure response is always valid JSON with required fields
        if not isinstance(final_state, dict):
            final_state = {"is_complete": False, "clarification_questions": ["Unexpected response format"]}
        
        # Guarantee required fields exist
        if "is_complete" not in final_state:
            final_state["is_complete"] = False
        
        return final_state
        
    except Exception as e:
        # CRITICAL: Always return valid JSON, never let exceptions break JSON format
        import traceback
        error_msg = f"An internal error occurred: {str(e)}"
        print(f"Chat endpoint error: {error_msg}")
        print(f"Traceback: {traceback.format_exc()}")
        
        return {
            "is_complete": False,
            "clarification_questions": [error_msg],
            "task_title": None,
            "user_query": user_query if 'user_query' in locals() else ""
        }


@app.get("/health", status_code=200)
def health_check():
    return {"status": "ok"}

# Voice Assistant WebSocket Endpoint
@app.websocket("/ws/voice")
async def voice_assistant_websocket(websocket: WebSocket, token: str = Query(...)):
    """WebSocket endpoint for voice assistant functionality with authentication."""
    try:
        # Authenticate user from token
        credentials_exception = HTTPException(
            status_code=401,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            username: str = payload.get("sub")
            if username is None:
                await websocket.close(code=4001, reason="Invalid token")
                return
        except JWTError:
            await websocket.close(code=4001, reason="Invalid token")
            return
        
        # Get user from database
        db = SessionLocal()
        try:
            user = crud.get_user_by_username(db, username=username)
            if user is None:
                await websocket.close(code=4001, reason="User not found")
                return
        finally:
            db.close()
        
        # Initialize voice assistant with user context
        voice_assistant = VoiceAssistant()
        await voice_assistant.websocket_endpoint(websocket, user_id=user.id)
        
    except Exception as e:
        print(f"WebSocket authentication error: {e}")
        await websocket.close(code=4002, reason="Authentication failed")

@app.post("/todos/", response_model=schemas.Todo)
def create_todo_endpoint(todo: schemas.TodoCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    try:
        return crud.create_todo(db=db, todo=todo, owner_id=current_user.id)
    except Exception as e:
        # Catches the "User is not a member" exception from the CRUD function
        raise HTTPException(status_code=403, detail=str(e))

@app.get("/todos/", response_model=List[schemas.Todo])
def read_todos_endpoint(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    todos = crud.get_relevant_todos_query(db, user_id=current_user.id).offset(skip).limit(limit).all()
    return todos

# Time Management Endpoints

@app.get("/todos/today", response_model=List[schemas.Todo])
def get_todos_today_endpoint(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return crud.get_todos_today(db, user_id=current_user.id)

@app.get("/todos/week", response_model=List[schemas.Todo])
def get_todos_for_week_endpoint(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return crud.get_todos_for_week(db, user_id=current_user.id)

@app.get("/todos/month", response_model=List[schemas.Todo])
def get_todos_for_month_endpoint(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return crud.get_todos_for_month(db, user_id=current_user.id)

@app.get("/todos/year", response_model=List[schemas.Todo])
def get_todos_for_year_endpoint(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return crud.get_todos_for_year(db, user_id=current_user.id)

@app.get("/todos/overdue", response_model=List[schemas.Todo])
def get_overdue_todos_endpoint(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return crud.get_overdue_todos(db, user_id=current_user.id)

@app.get("/todos/range", response_model=List[schemas.Todo])
def get_todos_by_date_range_endpoint(
    start_date: date, end_date: date, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    return crud.get_todos_by_date_range(db, user_id=current_user.id, start_date=start_date, end_date=end_date)

@app.get("/todos/{todo_id}", response_model=schemas.Todo)
def read_todo_endpoint(todo_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    db_todo = crud.get_todo(db, todo_id=todo_id)
    if db_todo is None:
        raise HTTPException(status_code=404, detail="Todo not found")
    if db_todo.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return db_todo

@app.put("/todos/{todo_id}", response_model=schemas.Todo)
def update_todo_endpoint(
    todo_id: int, todo: schemas.TodoUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    db_todo = crud.get_todo(db, todo_id=todo_id)
    if db_todo is None:
        raise HTTPException(status_code=404, detail="Todo not found")
    if db_todo.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    try:
        updated_todo = crud.update_todo(db, todo_id=todo_id, todo=todo, owner_id=current_user.id)
        return updated_todo
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))

@app.delete("/todos/{todo_id}", response_model=schemas.Todo)
def delete_todo_endpoint(todo_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    db_todo = crud.get_todo(db, todo_id=todo_id)
    if db_todo is None:
        raise HTTPException(status_code=404, detail="Todo not found")
    if db_todo.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    db_todo = crud.delete_todo(db, todo_id=todo_id)
    return db_todo

# --- Session Endpoints ---

@app.post("/sessions/", response_model=schemas.Session)
def create_team_session_endpoint(
    session: schemas.SessionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Create a new team session. The current user becomes the owner."""
    return crud.create_team_session(db=db, session=session, owner_id=current_user.id)

@app.get("/sessions/", response_model=List[schemas.UserSession])
def get_user_sessions_endpoint(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get all sessions the current user is a member of."""
    return crud.get_sessions_for_user(db, user_id=current_user.id)

@app.post("/sessions/{session_id}/invite")
def invite_user_to_session_endpoint(
    session_id: int,
    invite_data: schemas.SessionInvite,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Invite a user to a team session. Only the session owner can invite."""
    # 1. Verify the session exists
    db_session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")

    # 2. Verify the current user is the owner of the session
    if db_session.created_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the session owner can invite users")

    # 3. Invite the user
    new_member = crud.invite_user_to_session(db, session_id=session_id, invitee_email=invite_data.email)
    if not new_member:
        raise HTTPException(status_code=400, detail="User not found or is already a member of this session")

    return {"message": "User invited successfully"}

@app.get("/sessions/{session_id}/todos", response_model=List[schemas.Todo])
def get_session_todos_endpoint(
    session_id: int,
    user_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get all todos for a specific session.
    Only members of the session can access this.
    A user_id can be provided to filter todos by a specific creator.
    """
    # 1. Verify the session exists
    db_session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")

    # 2. Verify user is a member of the session
    member_check = db.query(models.SessionMember).filter(
        models.SessionMember.session_id == session_id,
        models.SessionMember.user_id == current_user.id
    ).first()
    if not member_check:
        raise HTTPException(status_code=403, detail="User is not a member of this session")

    # 3. Get the todos
    return crud.get_todos_by_session(db, session_id=session_id, requesting_user_id=current_user.id, filter_by_owner_id=user_id)

@app.get("/sessions/{session_id}/members", response_model=List[schemas.SessionMember])
def get_session_members_endpoint(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get all members of a specific session.
    Only members of the session can access this.
    """
    # 1. Verify the session exists
    db_session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")

    # 2. Verify user is a member of the session
    member_check = db.query(models.SessionMember).filter(
        models.SessionMember.session_id == session_id,
        models.SessionMember.user_id == current_user.id
    ).first()
    if not member_check:
        raise HTTPException(status_code=403, detail="User is not a member of this session")

    return crud.get_session_members(db, session_id=session_id)

@app.put("/sessions/{session_id}", response_model=schemas.Session)
def update_session_endpoint(
    session_id: int,
    session_update: schemas.SessionUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Allows the session owner to update a session's metadata.
    """
    try:
        updated_session = crud.update_session(db, session_id, session_update, current_user.id)
        return updated_session
    except ValueError as e:
        if "Only the session owner can update the session." in str(e):
            raise HTTPException(status_code=403, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/sessions/{session_id}/members/me")
def leave_session_endpoint(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Allows a user to leave a team session. If the user is the owner, the session will be deleted.
    """
    try:
        session_deleted = crud.remove_user_from_session(db, session_id, current_user.id)
        if session_deleted:
            return {"message": f"Session {session_id} deleted successfully."}
        else:
            return {"message": f"Successfully left session {session_id}"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/sessions/{session_id}/members/{member_user_id}")
def remove_session_member_endpoint(
    session_id: int,
    member_user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Allows the session owner to remove a specific member from a team session.
    The removed member's public todos will be reassigned to their private session.
    """
    try:
        crud.remove_session_member(db, session_id, member_user_id, current_user.id)
        return {"message": "Successfully left session"}
    except ValueError as e:
        if "Only the session owner can remove members" in str(e):
            raise HTTPException(status_code=403, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/sessions/{session_id}")
def delete_session_endpoint(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Allows the owner to delete a team session.
    Public todos in the session will be reassigned to their owners' private sessions.
    """
    try:
        crud.delete_session(db, session_id, current_user.id)
        return {"message": f"Session {session_id} deleted successfully."}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# --- User Endpoints ---

@app.post("/users/", response_model=schemas.User)
def create_user_endpoint(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user_by_username = crud.get_user_by_username(db, username=user.username)
    if db_user_by_username:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    if user.email:
        db_user_by_email = crud.get_user_by_email(db, email=user.email)
        if db_user_by_email:
            raise HTTPException(status_code=400, detail="Email already registered")

    return crud.create_user(db=db, user=user)

@app.get("/users/count", response_model=schemas.UserCount)
def get_user_count(db: Session = Depends(get_db)):
    """
    Get the total number of registered users.
    """
    count = crud.count_users(db)
    return {"total_users": count}

@app.post("/users/forgot-username", response_model=schemas.UsernameResponse)
def forgot_username(request: schemas.EmailVerificationRequest, db: Session = Depends(get_db)):
    """
    Retrieve a username by providing the associated email address.
    """
    user = crud.get_user_by_email(db, email=request.email)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User with this email not found",
        )
    return {"username": user.username}

@app.delete("/users/me")
def delete_current_user(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Allows an authenticated user to delete their own account and all associated data.
    """
    try:
        crud.delete_user(db, current_user.id)
        return {"message": "User and associated data deleted successfully."}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/users/me", response_model=schemas.User)
def read_users_me(current_user: models.User = Depends(get_current_user)):
    """
    Retrieve the current authenticated user's details.
    """
    return current_user

# --- Email Verification Endpoints ---

@app.post("/auth/request-verification")
async def request_verification(request: schemas.EmailVerificationRequest, db: Session = Depends(get_db)):
    """
    Request a verification code for email registration.
    """
    # 1. Check if email is already registered
    existing_user = crud.get_user_by_email(db, email=request.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # 2. Generate and store verification code (with rate limiting)
    plain_code, attempts_left = crud.create_verification_code(db, email=request.email)
    
    if plain_code is None:
        raise HTTPException(status_code=429, detail="Too many verification attempts. Please wait 5 hours before trying again.")

    try:
        await send_verification_email(email_to=request.email, code=plain_code)
    except Exception as e:
        # logger.error(f"Failed to send verification email to {request.email}: {e}")
        raise HTTPException(status_code=500, detail="Failed to send verification email.")

    return {"message": "Verification code sent successfully", "attempts_left": attempts_left}

@app.post("/auth/request-password-reset")
async def request_password_reset(request: schemas.EmailVerificationRequest, db: Session = Depends(get_db)):
    """
    Request a password reset code for an existing user.
    """
    # 1. Check if user exists
    user = crud.get_user_by_email(db, email=request.email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 2. Generate and store verification code (with rate limiting)
    plain_code, attempts_left = crud.create_verification_code(db, email=request.email)
    
    if plain_code is None:
        raise HTTPException(status_code=429, detail="Too many attempts. Try again later.")

    try:
        await send_verification_email(email_to=request.email, code=plain_code)
    except Exception as e:
        # logger.error(f"Failed to send password reset email to {request.email}: {e}")
        raise HTTPException(status_code=500, detail="Failed to send password reset email.")

    return {"message": "Password reset code sent", "username": user.username}

@app.post("/auth/forgot-password")
async def forgot_password(request: schemas.EmailVerificationRequest, db: Session = Depends(get_db)):
    """
    Request a password reset code for an existing user (alias for request_password_reset).
    """
    # 1. Check if user exists
    user = crud.get_user_by_email(db, email=request.email)
    if not user:
        raise HTTPException(status_code=404, detail="User with this email not found")

    # 2. Check for existing unexpired verification code (stricter rate limiting for password reset)
    existing_code = crud.get_verification_code(db, email=request.email)
    if existing_code and existing_code.expires_at > datetime.utcnow():
        time_since_creation = datetime.utcnow() - existing_code.created_at
        wait_time = timedelta(hours=5) - time_since_creation
        raise HTTPException(
            status_code=429,
            detail=f"Please wait before requesting another code. Try again in {wait_time}."
        )

    # 3. Generate and store verification code
    plain_code, attempts_left = crud.create_verification_code(db, email=request.email)
    
    if plain_code is None:
        raise HTTPException(status_code=429, detail="Too many verification attempts. Please wait 5 hours before trying again.")

    try:
        await send_verification_email(email_to=request.email, code=plain_code)
    except Exception as e:
        # logger.error(f"Failed to send password reset email to {request.email}: {e}")
        raise HTTPException(status_code=500, detail="Failed to send password reset email.")

    return {"message": "Password reset code sent", "username": user.username}

@app.post("/auth/reset-password")
def reset_password(request: schemas.PasswordReset, db: Session = Depends(get_db)):
    """
    Reset a user's password using a valid verification code.
    """
    # 1. Verify the code is valid and not expired
    if not crud.verify_code(db, email=request.email, code=request.code):
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired verification code",
        )

    # 2. Get the user
    user = crud.get_user_by_email(db, email=request.email)
    if not user:
        # This case is unlikely if verify_code passed, but it's a good safeguard
        raise HTTPException(status_code=404, detail="User not found")
    
    # 3. Update the password
    crud.update_user_password(db, user=user, new_password=request.new_password)

    # Invalidate the used verification code by deleting it
    db.query(models.EmailVerification).filter(models.EmailVerification.email == request.email).delete()
    db.commit()

    return {"message": "Password has been reset successfully"}

@app.post("/auth/register", response_model=schemas.Token)
def register_user(user_data: schemas.UserCreateAndVerify, db: Session = Depends(get_db)):
    """
    Register a new user after verifying the email code.
    """
    # 1. Verify the code
    is_valid = crud.verify_code(db, email=user_data.email, code=user_data.code)
    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired verification code",
        )
        
    # 2. Check for existing user (double-check)
    db_user_by_username = crud.get_user_by_username(db, username=user_data.username)
    if db_user_by_username:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    db_user_by_email = crud.get_user_by_email(db, email=user_data.email)
    if db_user_by_email:
        raise HTTPException(status_code=400, detail="Email already registered")

    # 3. Create the user
    new_user = crud.create_user(db=db, user=user_data)
    
    # 4. Return an access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": new_user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# --- Authentication Endpoint ---

@app.post("/token", response_model=schemas.Token)
def login_for_access_token(db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Handles token generation for user authentication.
    """
    user = crud.authenticate_user(db, username=form_data.username, password=form_data.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # Create access token for the user
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"} 