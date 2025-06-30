from pydantic import BaseModel
from typing import Optional

class ToDoBase(BaseModel):
    title: str
    description: Optional[str] = None

class ToDoCreate(ToDoBase):
    pass

class ToDoUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    done: Optional[bool] = None

class ToDo(ToDoBase):
    id: int
    done: bool

    class Config:
        from_attributes = True 