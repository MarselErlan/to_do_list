from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import date, time, datetime
from pydantic import EmailStr

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
    session_id: Optional[int] = None
    is_private: Optional[bool] = None
    is_global_public: Optional[bool] = None

class TodoUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    done: Optional[bool] = None
    start_date: Optional[date] = None
    start_time: Optional[time] = None
    end_date: Optional[date] = None
    end_time: Optional[time] = None
    due_date: Optional[date] = None
    session_id: Optional[int] = None

class Todo(TodoBase):
    id: int
    done: bool
    owner_id: int
    created_at: datetime
    is_private: bool
    is_global_public: bool = False
    session_id: int | None = None

    model_config = ConfigDict(from_attributes=True)

# User Schemas
class UserBase(BaseModel):
    username: str
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    is_active: bool
    todos: List["Todo"] = []
    model_config = ConfigDict(from_attributes=True)

# Token Schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class EmailVerificationRequest(BaseModel):
    email: EmailStr

class EmailVerificationCode(BaseModel):
    email: EmailStr
    code: str

class UserCreateAndVerify(UserCreate):
    code: str = Field(..., alias="verification_code")

class PasswordResetRequestResponse(BaseModel):
    message: str
    username: str

class UserCount(BaseModel):
    total_users: int

class UsernameResponse(BaseModel):
    username: str

class PasswordReset(BaseModel):
    email: EmailStr
    code: str
    new_password: str

# --- Session Schemas ---

class SessionBase(BaseModel):
    name: str

class SessionCreate(SessionBase):
    pass

class SessionUpdate(BaseModel):
    name: Optional[str] = None

class Session(SessionBase):
    id: int
    created_by_id: int

    class Config:
        from_attributes = True

class UserSession(BaseModel):
    id: int
    name: str | None
    role: str

    class Config:
        from_attributes = True

class SessionMember(BaseModel):
    user_id: int
    username: str
    role: str

    class Config:
        from_attributes = True

class SessionInvite(BaseModel):
    email: EmailStr

# --- User Schemas ---
class UserBase(BaseModel):
    username: str
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    is_active: bool
    todos: List["Todo"] = []
    model_config = ConfigDict(from_attributes=True)

class MessageResponse(BaseModel):
    message: str

class VerificationRequestResponse(BaseModel):
    message: str
    attempts_left: int

# --- Chat Schemas ---
class ChatRequest(BaseModel):
    user_query: str
    # In the future, you could add conversation history here
    # history: List[dict] = [] 