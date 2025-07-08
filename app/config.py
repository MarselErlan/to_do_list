from pydantic_settings import BaseSettings
import os
from pydantic import EmailStr
from typing import Optional

class Settings(BaseSettings):
    DATABASE_URL: str
    OPENAI_API_KEY: str
    LANGCHAIN_TRACING_V2: bool = False
    LANGCHAIN_API_KEY: str | None = None
    LANGCHAIN_PROJECT: str | None = None
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