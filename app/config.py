from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    database_url: Optional[str] = "postgresql://user:password@localhost/todo_db"

    class Config:
        env_file = ".env"

settings = Settings() 