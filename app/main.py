from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
from datetime import date, datetime, timedelta
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.routing import APIRoute
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from jose import JWTError, jwt

from . import crud, models, schemas
from .database import SessionLocal, engine
from .security import create_access_token
from .config import settings
from .email import send_verification_email

# models.Base.metadata.create_all(bind=engine) # This should be handled by Alembic in production

app = FastAPI(
    title="Todo List API",
    description="A simple todo list API built with FastAPI",
    version="1.0.0"
)

# Custom middleware to handle OPTIONS requests
class OptionsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":
            response = Response(status_code=204)
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
            response.headers["Access-Control-Allow-Headers"] = "*"
            response.headers["Access-Control-Max-Age"] = "86400"
            return response
        return await call_next(request)

# Add OPTIONS middleware first
app.add_middleware(OptionsMiddleware)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Handle OPTIONS requests for CORS preflight
@app.options("/{path:path}")
async def options_handler(request: Request):
    return Response(status_code=204)

@app.get("/health", status_code=200)
def health_check():
    return {"status": "ok"}

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

@app.post("/todos/", response_model=schemas.Todo)
def create_todo_endpoint(todo: schemas.TodoCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return crud.create_todo(db=db, todo=todo, owner_id=current_user.id)

@app.get("/todos/", response_model=List[schemas.Todo])
def read_todos_endpoint(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    todos = crud.get_todos_by_user(db, user_id=current_user.id, skip=skip, limit=limit)
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
    
    db_todo = crud.update_todo(db, todo_id=todo_id, todo=todo)
    return db_todo

@app.delete("/todos/{todo_id}", response_model=schemas.Todo)
def delete_todo_endpoint(todo_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    db_todo = crud.get_todo(db, todo_id=todo_id)
    if db_todo is None:
        raise HTTPException(status_code=404, detail="Todo not found")
    if db_todo.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    db_todo = crud.delete_todo(db, todo_id=todo_id)
    return db_todo

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

# --- Email Verification Endpoints ---

@app.post("/auth/request-verification")
async def request_verification_code(
    request: schemas.EmailVerificationRequest, 
    db: Session = Depends(get_db)
):
    """
    Request a verification code for an email address.
    This will generate a code, save it, and email it.
    """
    # Check if user already exists
    db_user = crud.get_user_by_email(db, email=request.email)
    if db_user:
        raise HTTPException(status_code=400, detail="An account with this email already exists.")

    code = crud.create_verification_code(db, email=request.email)
    
    await send_verification_email(email_to=request.email, code=code)
    
    return {"message": "Verification code sent successfully"}

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