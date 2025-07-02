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