from sqlalchemy.orm import Session
from datetime import date, timedelta, datetime
from . import models, schemas

def get_todo(db: Session, todo_id: int):
    return db.query(models.ToDo).filter(models.ToDo.id == todo_id).first()

def get_todos(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.ToDo).offset(skip).limit(limit).all()

def create_todo(db: Session, todo: schemas.ToDoCreate):
    db_todo = models.ToDo(
        title=todo.title, 
        description=todo.description,
        done=todo.done if todo.done is not None else False,
        start_time=todo.start_time,
        end_time=todo.end_time,
        due_date=todo.due_date
    )
    db.add(db_todo)
    db.commit()
    db.refresh(db_todo)
    return db_todo

def update_todo(db: Session, todo_id: int, todo: schemas.ToDoUpdate):
    db_todo = get_todo(db, todo_id)
    if db_todo:
        update_data = todo.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_todo, key, value)
        db.commit()
        db.refresh(db_todo)
    return db_todo

def delete_todo(db: Session, todo_id: int):
    db_todo = get_todo(db, todo_id)
    if db_todo:
        db.delete(db_todo)
        db.commit()
    return db_todo

# Time Management Functions

def get_todos_for_today(db: Session):
    """Get todos due today"""
    today = date.today()
    return db.query(models.ToDo).filter(models.ToDo.due_date == today).all()

def get_todos_for_week(db: Session):
    """Get todos due this week (Monday to Sunday)"""
    today = date.today()
    days_since_monday = today.weekday()
    week_start = today - timedelta(days=days_since_monday)
    week_end = week_start + timedelta(days=6)
    
    return db.query(models.ToDo).filter(
        models.ToDo.due_date >= week_start,
        models.ToDo.due_date <= week_end
    ).all()

def get_todos_for_month(db: Session):
    """Get todos due this month"""
    today = date.today()
    month_start = today.replace(day=1)
    
    # Calculate next month's first day
    if today.month == 12:
        next_month_start = today.replace(year=today.year + 1, month=1, day=1)
    else:
        next_month_start = today.replace(month=today.month + 1, day=1)
    
    month_end = next_month_start - timedelta(days=1)
    
    return db.query(models.ToDo).filter(
        models.ToDo.due_date >= month_start,
        models.ToDo.due_date <= month_end
    ).all()

def get_todos_for_year(db: Session):
    """Get todos due this year"""
    today = date.today()
    year_start = today.replace(month=1, day=1)
    year_end = today.replace(month=12, day=31)
    
    return db.query(models.ToDo).filter(
        models.ToDo.due_date >= year_start,
        models.ToDo.due_date <= year_end
    ).all()

def get_overdue_todos(db: Session):
    """Get todos that are overdue (due date is in the past and not completed)"""
    today = date.today()
    return db.query(models.ToDo).filter(
        models.ToDo.due_date < today,
        models.ToDo.done == False
    ).all()

def get_todos_by_time_range(db: Session, start_time: datetime, end_time: datetime):
    """Get todos within a specific time range"""
    return db.query(models.ToDo).filter(
        models.ToDo.start_time >= start_time,
        models.ToDo.start_time <= end_time
    ).all()

def get_todos_by_date_range(db: Session, start_date: date, end_date: date):
    """Get todos within a specific date range"""
    return db.query(models.ToDo).filter(
        models.ToDo.due_date >= start_date,
        models.ToDo.due_date <= end_date
    ).all()

 