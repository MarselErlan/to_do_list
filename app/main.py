from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
from datetime import date, datetime, timedelta
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.routing import APIRoute
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from jose import JWTError, jwt

from . import crud, models, schemas, llm_service
from .database import SessionLocal, engine, get_db, init_db
from .security import create_access_token, verify_password, get_password_hash
from .config import settings
from .email import send_verification_email

# Global variable to hold the graph instance
task_creation_graph = None

# Initialize database tables
init_db()

app = FastAPI(
    title="Todo List API",
    description="A simple todo list API built with FastAPI",
    version="1.0.0"
)

@app.on_event("startup")
def startup_event():
    """
    Initializes the LangGraph instance when the application starts.
    """
    global task_creation_graph
    # This creates the graph with the actual OpenAI LLM
    task_creation_graph = llm_service.create_graph()
    print("--- Task Creation Graph Initialized ---")


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://v0-recreate-ui-from-s-git-9b108d-ethanabduraimov-7965s-projects.vercel.app",
        "*"  # Allow all origins temporarily
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
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
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
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
    """
    if not task_creation_graph:
        raise HTTPException(status_code=500, detail="Graph not initialized")

    # Initial state for the graph, ensuring all keys are present
    initial_state = {
        "user_query": request.user_query,
        "task_title": None,
        "description": None,
        "is_private": True,  # Default to private
        "is_global_public": False,
        "session_name": None,
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
    
    return final_state


@app.get("/health", status_code=200)
def health_check():
    return {"status": "ok"}

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

@app.post("/auth/request-verification", response_model=schemas.VerificationRequestResponse)
async def request_verification_code(
    request: schemas.EmailVerificationRequest, 
    db: Session = Depends(get_db)
):
    # Check if user already exists
    db_user = crud.get_user_by_email(db, email=request.email)
    if db_user:
        raise HTTPException(status_code=400, detail="An account with this email already exists.")

    # Create or update the verification code and get attempts left
    plain_code, attempts_left = crud.create_verification_code(db, email=request.email)

    if plain_code is None:
        # This means the attempt limit has been reached
        raise HTTPException(
            status_code=429, 
            detail=f"Too many verification attempts. Please wait 5 hours before trying again."
        )

    await send_verification_email(email_to=request.email, code=plain_code)
    return {"message": "Verification code sent successfully", "attempts_left": attempts_left}

@app.post("/auth/forgot-password", response_model=schemas.PasswordResetRequestResponse)
async def forgot_password(
    request: schemas.EmailVerificationRequest,
    db: Session = Depends(get_db)
):
    """
    Request a password reset code.
    This will check for a user and enforce a rate limit.
    """
    # 1. Check if user exists
    user = crud.get_user_by_email(db, email=request.email)
    if not user:
        raise HTTPException(status_code=404, detail="User with this email not found")

    # 2. Check for rate-limiting
    existing_code = crud.get_verification_code(db, email=request.email)
    if existing_code:
        time_since_creation = datetime.utcnow() - existing_code.created_at
        if time_since_creation < timedelta(hours=5):
            wait_time = timedelta(hours=5) - time_since_creation
            raise HTTPException(
                status_code=429,
                detail=f"Please wait before requesting another code. Try again in {wait_time}."
            )

    # 3. Create and send new code
    code = crud.create_verification_code(db, email=request.email)
    await send_verification_email(email_to=request.email, code=code)

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
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": new_user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# --- Authentication Endpoint ---

@app.post("/token", response_model=schemas.Token)
def login_for_access_token(db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()):
    user = crud.authenticate_user(db, username=form_data.username, password=form_data.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"} 