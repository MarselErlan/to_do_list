from sqlalchemy import Boolean, Column, Integer, String, DateTime, Date, Time, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .database import Base
from datetime import datetime, timedelta

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=True)
    phone_number = Column(String, unique=True, index=True, nullable=True)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)

    todos = relationship("Todo", back_populates="owner")
    sessions = relationship("SessionMember", back_populates="user")


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

    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=True)
    session = relationship("Session", back_populates="todos")
    is_private = Column(Boolean, default=True, nullable=False)
    is_global_public = Column(Boolean, default=False, nullable=False)


class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=True) # Name for team sessions
    created_by_id = Column("created_by", Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    creator = relationship("User")
    members = relationship("SessionMember", back_populates="session")
    todos = relationship("Todo", back_populates="session")


class SessionMember(Base):
    __tablename__ = "session_members"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(String, default='collaborator', nullable=False) # owner, collaborator
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    session = relationship("Session", back_populates="members")
    user = relationship("User", back_populates="sessions")


class EmailVerification(Base):
    __tablename__ = "email_verifications"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    code = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, default=lambda: datetime.utcnow() + timedelta(hours=5))
    attempts = Column(Integer, default=1, nullable=False)
    verified = Column(Boolean, default=False) 