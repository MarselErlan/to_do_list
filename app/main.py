from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
from datetime import date, datetime

from . import crud, models, schemas
from .database import SessionLocal, engine

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Todo List API",
    description="A simple todo list API built with FastAPI",
    version="1.0.0"
)

# Add CORS middleware - THIS IS REQUIRED FOR YOUR FRONTEND
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, use your specific domain
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

@app.post("/todos/", response_model=schemas.ToDo)
def create_todo_endpoint(todo: schemas.ToDoCreate, db: Session = Depends(get_db)):
    return crud.create_todo(db=db, todo=todo)

@app.get("/todos/", response_model=List[schemas.ToDo])
def read_todos_endpoint(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    todos = crud.get_todos(db, skip=skip, limit=limit)
    return todos

# Time Management Endpoints

@app.get("/todos/today", response_model=List[schemas.ToDo])
def get_todos_today_endpoint(db: Session = Depends(get_db)):
    """Get todos due today"""
    return crud.get_todos_for_today(db)

@app.get("/todos/week", response_model=List[schemas.ToDo])
def get_todos_week_endpoint(db: Session = Depends(get_db)):
    """Get todos due this week"""
    return crud.get_todos_for_week(db)

@app.get("/todos/month", response_model=List[schemas.ToDo])
def get_todos_month_endpoint(db: Session = Depends(get_db)):
    """Get todos due this month"""
    return crud.get_todos_for_month(db)

@app.get("/todos/year", response_model=List[schemas.ToDo])
def get_todos_year_endpoint(db: Session = Depends(get_db)):
    """Get todos due this year"""
    return crud.get_todos_for_year(db)

@app.get("/todos/overdue", response_model=List[schemas.ToDo])
def get_overdue_todos_endpoint(db: Session = Depends(get_db)):
    """Get overdue todos (past due date and not completed)"""
    return crud.get_overdue_todos(db)

@app.get("/todos/range", response_model=List[schemas.ToDo])
def get_todos_by_date_range_endpoint(
    start_date: date = Query(..., description="Start date for filtering"),
    end_date: date = Query(..., description="End date for filtering"),
    db: Session = Depends(get_db)
):
    """Get todos within a specific date range"""
    return crud.get_todos_by_date_range(db, start_date, end_date)

@app.get("/todos/{todo_id}", response_model=schemas.ToDo)
def read_todo_endpoint(todo_id: int, db: Session = Depends(get_db)):
    db_todo = crud.get_todo(db, todo_id=todo_id)
    if db_todo is None:
        raise HTTPException(status_code=404, detail="ToDo not found")
    return db_todo

@app.put("/todos/{todo_id}", response_model=schemas.ToDo)
def update_todo_endpoint(todo_id: int, todo: schemas.ToDoUpdate, db: Session = Depends(get_db)):
    db_todo = crud.update_todo(db, todo_id=todo_id, todo=todo)
    if db_todo is None:
        raise HTTPException(status_code=404, detail="ToDo not found")
    return db_todo

@app.delete("/todos/{todo_id}", response_model=schemas.ToDo)
def delete_todo_endpoint(todo_id: int, db: Session = Depends(get_db)):
    db_todo = crud.delete_todo(db, todo_id=todo_id)
    if db_todo is None:
        raise HTTPException(status_code=404, detail="ToDo not found")
    return db_todo 