from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
from datetime import date, datetime
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.routing import APIRoute

from . import crud, models, schemas
from .database import SessionLocal, engine

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

# Add CORS middleware with permissive settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# Handle OPTIONS requests for CORS preflight
@app.options("/{path:path}")
async def options_handler(request: Request):
    return Response(status_code=204)

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/todos/", response_model=schemas.Todo)
def create_todo_endpoint(todo: schemas.TodoCreate, db: Session = Depends(get_db)):
    return crud.create_todo(db=db, todo=todo)

@app.get("/todos/", response_model=List[schemas.Todo])
def read_todos_endpoint(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    todos = crud.get_todos(db, skip=skip, limit=limit)
    return todos

# Time Management Endpoints

@app.get("/todos/today", response_model=List[schemas.Todo])
def get_todos_today_endpoint(db: Session = Depends(get_db)):
    return crud.get_todos_today(db)

@app.get("/todos/week", response_model=List[schemas.Todo])
def get_todos_for_week_endpoint(db: Session = Depends(get_db)):
    return crud.get_todos_for_week(db)

@app.get("/todos/month", response_model=List[schemas.Todo])
def get_todos_for_month_endpoint(db: Session = Depends(get_db)):
    return crud.get_todos_for_month(db)

@app.get("/todos/year", response_model=List[schemas.Todo])
def get_todos_for_year_endpoint(db: Session = Depends(get_db)):
    return crud.get_todos_for_year(db)

@app.get("/todos/overdue", response_model=List[schemas.Todo])
def get_overdue_todos_endpoint(db: Session = Depends(get_db)):
    return crud.get_overdue_todos(db)

@app.get("/todos/range", response_model=List[schemas.Todo])
def get_todos_by_date_range_endpoint(
    start_date: date, end_date: date, db: Session = Depends(get_db)
):
    return crud.get_todos_by_date_range(db, start_date, end_date)

@app.get("/todos/{todo_id}", response_model=schemas.Todo)
def read_todo_endpoint(todo_id: int, db: Session = Depends(get_db)):
    db_todo = crud.get_todo(db, todo_id=todo_id)
    if db_todo is None:
        raise HTTPException(status_code=404, detail="Todo not found")
    return db_todo

@app.put("/todos/{todo_id}", response_model=schemas.Todo)
def update_todo_endpoint(
    todo_id: int, todo: schemas.TodoUpdate, db: Session = Depends(get_db)
):
    db_todo = crud.update_todo(db, todo_id=todo_id, todo=todo)
    if db_todo is None:
        raise HTTPException(status_code=404, detail="Todo not found")
    return db_todo

@app.delete("/todos/{todo_id}", response_model=schemas.Todo)
def delete_todo_endpoint(todo_id: int, db: Session = Depends(get_db)):
    db_todo = crud.delete_todo(db, todo_id=todo_id)
    if db_todo is None:
        raise HTTPException(status_code=404, detail="Todo not found")
    return db_todo 