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

    class Config:
        env_file = ".env"

settings = Settings() 