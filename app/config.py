from pydantic_settings import BaseSettings, SettingsConfigDict
import os
from pydantic import EmailStr

class Settings(BaseSettings):
    database_url: str
    port: int = 8000

    # JWT Settings
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # Mail settings
    mail_username: str
    mail_password: str
    mail_from: EmailStr
    mail_port: int
    mail_server: str
    mail_starttls: bool
    mail_ssl_tls: bool
    use_credentials: bool = True
    validate_certs: bool = True
    template_folder: str = "app/email_templates"
    suppress_send: bool = False

    model_config = SettingsConfigDict(env_file=".env")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Railway provides DATABASE_URL automatically for PostgreSQL
        if os.getenv("DATABASE_URL"):
            self.database_url = os.getenv("DATABASE_URL")

settings = Settings() 