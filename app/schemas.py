from pydantic import BaseModel
from typing import Optional, List
from datetime import date, time

# User Schemas
class UserBase(BaseModel):
    username: str
    email: Optional[str] = None
    phone_number: Optional[str] = None

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    is_active: bool
    
    class Config:
        from_attributes = True

# Todo Schemas
class TodoBase(BaseModel):
    title: str
    description: Optional[str] = None
    start_date: Optional[date] = None
    start_time: Optional[time] = None
    end_date: Optional[date] = None
    end_time: Optional[time] = None
    due_date: Optional[date] = None

class TodoCreate(TodoBase):
    done: bool = False

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
    done: bool
    owner_id: int
    
    class Config:
        from_attributes = True

# Add relationships to User schema
class User(UserBase):
    id: int
    is_active: bool
    todos: List[Todo] = []
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None 