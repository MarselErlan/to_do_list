from pydantic_settings import BaseSettings
import os

class Settings(BaseSettings):
    database_url: str = "sqlite:///./test.db"  # Default for local development
    port: int = 8000

    # JWT Settings
    secret_key: str = "a-very-secret-key-that-should-be-in-a-config-file"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    class Config:
        env_file = ".env"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Railway provides DATABASE_URL automatically for PostgreSQL
        if os.getenv("DATABASE_URL"):
            self.database_url = os.getenv("DATABASE_URL")

settings = Settings() 