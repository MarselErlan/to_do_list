from pydantic_settings import BaseSettings, SettingsConfigDict
import os
from pydantic import EmailStr
from typing import Optional

class Settings(BaseSettings):
    database_url: str
    port: int = 8000

    # JWT Settings
    secret_key: str = "fallback-secret-key-for-development"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # Mail settings (optional for migrations)
    mail_username: Optional[str] = None
    mail_password: Optional[str] = None
    mail_from: Optional[EmailStr] = None
    mail_port: Optional[int] = None
    mail_server: Optional[str] = None
    mail_starttls: Optional[bool] = None
    mail_ssl_tls: Optional[bool] = None
    use_credentials: bool = True
    validate_certs: bool = True
    template_folder: str = "app/email_templates"
    suppress_send: bool = False

    model_config = SettingsConfigDict(extra='ignore')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Railway provides DATABASE_URL automatically for PostgreSQL
        if os.getenv("DATABASE_URL"):
            self.database_url = os.getenv("DATABASE_URL")

settings = Settings() 