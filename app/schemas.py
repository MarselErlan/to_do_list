from pydantic import BaseModel
from datetime import datetime, date, time
from typing import Optional

class TodoBase(BaseModel):
    title: str
    description: Optional[str] = None
    done: bool = False
    start_date: Optional[date] = None
    start_time: Optional[time] = None
    end_date: Optional[date] = None
    end_time: Optional[time] = None
    due_date: Optional[date] = None

class TodoCreate(TodoBase):
    pass

class TodoUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    done: Optional[bool] = None
    start_date: Optional[date] = None
    start_time: Optional[time] = None
    end_date: Optional[date] = None
    end_time: Optional[time] = None
    due_date: Optional[date] = None

class Todo(TodoBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True 