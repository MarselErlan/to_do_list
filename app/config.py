from pydantic_settings import BaseSettings
import os
from pydantic import EmailStr
from typing import Optional

class Settings(BaseSettings):
    DATABASE_URL: str
    OPENAI_API_KEY: str
    SECRET_KEY: str = "default-secret-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # LangSmith Configuration - Updated for LangGraph Architecture
    LANGCHAIN_TRACING_V2: bool = True  # Enable tracing for LangGraph
    LANGCHAIN_ENDPOINT: str = "https://api.smith.langchain.com"
    LANGCHAIN_API_KEY: str | None = None
    LANGCHAIN_PROJECT: str = "TaskFlow-TodoList-Production"  # Project name for this app
    
    # LangGraph specific tracing
    LANGCHAIN_SESSION: str | None = None  # Optional: for grouping traces
    
    SENDGRID_API_KEY: str | None = None

    # Mail settings
    MAIL_USERNAME: Optional[str] = None
    MAIL_PASSWORD: Optional[str] = None
    MAIL_FROM: Optional[EmailStr] = None
    MAIL_PORT: Optional[int] = None
    MAIL_SERVER: Optional[str] = None
    MAIL_STARTTLS: bool = False
    MAIL_SSL_TLS: bool = False
    SUPPRESS_SEND: bool = False

    class Config:
        env_file = ".env"
        extra='ignore'

settings = Settings() 