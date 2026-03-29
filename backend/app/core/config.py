from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://uute:uute_password@localhost:5432/uute_db"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # File storage
    upload_dir: Path = Path("/var/uute-service/uploads")

    # SMTP
    smtp_host: str = "smtp.yourdomain.ru"
    smtp_port: int = 465
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@yourdomain.ru"
    smtp_from_name: str = "УУТЭ Проектировщик"
    smtp_use_ssl: bool = True

    # Admin
    admin_email: str = "admin@yourdomain.ru"
    admin_api_key: str = "change-me-in-production"

    # App
    app_base_url: str = "http://localhost:8000"
    max_retry_count: int = 3

    # Templates
    templates_dir: Path = Path(__file__).parent.parent.parent / "templates"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
