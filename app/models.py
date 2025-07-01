from sqlalchemy import Boolean, Column, Integer, String, DateTime, Date, Time, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=True)
    phone_number = Column(String, unique=True, index=True, nullable=True)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)

    todos = relationship("Todo", back_populates="owner")

class Todo(Base):
    __tablename__ = "todos"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(String, index=True)
    done = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    start_date = Column(Date, nullable=True)
    start_time = Column(Time, nullable=True)
    end_date = Column(Date, nullable=True)
    end_time = Column(Time, nullable=True)
    due_date = Column(Date, nullable=True)

    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="todos") 