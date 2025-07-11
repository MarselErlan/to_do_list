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

    # Google Cloud Voice Assistant Settings
    GOOGLE_APPLICATION_CREDENTIALS: Optional[str] = None  # Path to service account JSON
    GOOGLE_CLOUD_PROJECT: Optional[str] = None  # Your GCP project ID
    GOOGLE_CLOUD_CREDENTIALS_JSON: Optional[str] = None  # JSON content as string (for Railway)
    SPEECH_LANGUAGE: str = "en-US"  # Default language for speech recognition
    SPEECH_ENCODING: str = "LINEAR16"  # Default encoding
    SPEECH_SAMPLE_RATE: int = 16000  # Default sample rate

    class Config:
        env_file = ".env"
        extra='ignore'

settings = Settings() 