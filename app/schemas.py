from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime, date

class ToDoBase(BaseModel):
    title: str
    description: Optional[str] = None

class ToDoCreate(ToDoBase):
    done: Optional[bool] = False
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    due_date: Optional[date] = None

class ToDoUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    done: Optional[bool] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    due_date: Optional[date] = None

class ToDo(ToDoBase):
    id: int
    done: bool
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    due_date: Optional[date] = None

    model_config = ConfigDict(from_attributes=True) 