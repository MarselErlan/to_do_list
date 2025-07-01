from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date
from .database import Base

class ToDo(Base):
    __tablename__ = "todos"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(String, index=True)
    done = Column(Boolean, default=False)
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    due_date = Column(Date, nullable=True) 