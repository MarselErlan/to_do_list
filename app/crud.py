from sqlalchemy.orm import Session
from datetime import date, timedelta, datetime
from typing import Optional
from . import models, schemas
from .security import get_password_hash, verify_password

# User CRUD Functions

def authenticate_user(db: Session, username: str, password: str) -> Optional[models.User]:
    """
    Authenticates a user by checking the username and password.
    Returns the user object if authentication is successful, otherwise None.
    """
    user = get_user_by_username(db, username=username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.User).offset(skip).limit(limit).all()

def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# Todo CRUD Functions

def get_todo(db: Session, todo_id: int):
    return db.query(models.Todo).filter(models.Todo.id == todo_id).first()

def get_todos_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.Todo).filter(models.Todo.owner_id == user_id).offset(skip).limit(limit).all()

def create_todo(db: Session, todo: schemas.TodoCreate, owner_id: int):
    db_todo = models.Todo(
        **todo.model_dump(),
        owner_id=owner_id
    )
    db.add(db_todo)
    db.commit()
    db.refresh(db_todo)
    return db_todo

def update_todo(db: Session, todo_id: int, todo: schemas.TodoUpdate):
    db_todo = db.query(models.Todo).filter(models.Todo.id == todo_id).first()
    if db_todo:
        update_data = todo.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_todo, key, value)
        db.commit()
        db.refresh(db_todo)
    return db_todo

def delete_todo(db: Session, todo_id: int):
    db_todo = db.query(models.Todo).filter(models.Todo.id == todo_id).first()
    if db_todo:
        db.delete(db_todo)
        db.commit()
    return db_todo

# Time Management Functions

def get_todos_today(db: Session, user_id: int):
    """Get todos for a specific user due today"""
    today = date.today()
    return db.query(models.Todo).filter(
        models.Todo.owner_id == user_id,
        models.Todo.due_date == today
    ).all()

def get_todos_for_week(db: Session, user_id: int):
    """Get todos for a specific user due this week"""
    today = date.today()
    days_since_monday = today.weekday()
    week_start = today - timedelta(days=days_since_monday)
    week_end = week_start + timedelta(days=6)
    
    return db.query(models.Todo).filter(
        models.Todo.owner_id == user_id,
        models.Todo.due_date != None,
        models.Todo.due_date >= week_start,
        models.Todo.due_date <= week_end
    ).all()

def get_todos_for_month(db: Session, user_id: int):
    """Get todos for a specific user due this month"""
    today = date.today()
    month_start = today.replace(day=1)
    
    if today.month == 12:
        next_month_start = today.replace(year=today.year + 1, month=1, day=1)
    else:
        next_month_start = today.replace(month=today.month + 1, day=1)
    
    month_end = next_month_start - timedelta(days=1)
    
    return db.query(models.Todo).filter(
        models.Todo.owner_id == user_id,
        models.Todo.due_date != None,
        models.Todo.due_date >= month_start,
        models.Todo.due_date <= month_end
    ).all()

def get_todos_for_year(db: Session, user_id: int):
    """Get todos for a specific user due this year"""
    today = date.today()
    year_start = today.replace(month=1, day=1)
    year_end = today.replace(month=12, day=31)
    
    return db.query(models.Todo).filter(
        models.Todo.owner_id == user_id,
        models.Todo.due_date != None,
        models.Todo.due_date >= year_start,
        models.Todo.due_date <= year_end
    ).all()

def get_overdue_todos(db: Session, user_id: int):
    """Get overdue todos for a specific user"""
    today = date.today()
    return db.query(models.Todo).filter(
        models.Todo.owner_id == user_id,
        models.Todo.due_date != None,
        models.Todo.due_date < today,
        models.Todo.done == False
    ).all()

def get_todos_by_time_range(db: Session, start_time: datetime, end_time: datetime):
    """Get todos within a specific time range"""
    return db.query(models.Todo).filter(
        models.Todo.start_time >= start_time,
        models.Todo.start_time <= end_time
    ).all()

def get_todos_by_date(db: Session, target_date: date):
    return db.query(models.Todo).filter(models.Todo.due_date == target_date).all()

def get_todos_by_date_range(db: Session, user_id: int, start_date: date, end_date: date):
    return db.query(models.Todo).filter(
        models.Todo.owner_id == user_id,
        models.Todo.due_date.between(start_date, end_date)
    ).all()

 