from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings


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
    # SMTP пароль — секрет, обязателен в .env. Без него отправка писем сразу
    # ломается, поэтому лучше упасть на старте.
    smtp_password: str = Field(..., min_length=1, description="Пароль SMTP (REQUIRED)")
    smtp_from: str = "noreply@yourdomain.ru"
    smtp_from_name: str = "УУТЭ Проектировщик"
    smtp_use_ssl: bool = True

    # Admin
    admin_email: str = "admin@yourdomain.ru"
    # Ключ админки — обязателен. Любой дефолт = доступ всем подряд.
    admin_api_key: str = Field(..., min_length=16, description="API-ключ админки (REQUIRED, ≥16 симв.)")

    # LLM (OpenRouter) — обязателен в .env, без него парсинг ТУ не работает.
    openrouter_api_key: str = Field(..., min_length=10, description="OpenRouter API key (REQUIRED)")
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "google/gemini-2.5-flash"

    # App
    app_base_url: str = "http://localhost:8000"
    max_retry_count: int = 3

    # CORS: список разрешённых origin-ов для браузерных запросов с лендинга/админки.
    # ENV: CORS_ORIGINS='["https://constructproject.ru","http://localhost:5173"]'
    # (Pydantic v2 парсит список из JSON.)
    cors_origins: list[str] = Field(
        default_factory=lambda: ["https://constructproject.ru"],
        description="Разрешённые origin-ы для CORS (JSON-список в ENV)",
    )

    # Реквизиты компании (для договоров и счетов)
    company_full_name: str = "ИП Анищенко Сергей Сергеевич"
    company_inn: str = "280103456296"
    company_ogrn: str = "305280120300026"
    company_address: str = "675000, Амурская область, г. Благовещенск, ул. Нагорная, 17-18"
    company_bank_name: str = "Филиал «Центральный» Банка ВТБ (ПАО)"
    company_bik: str = "044525411"
    company_corr_account: str = "30101810145250000411"
    company_settlement_account: str = "40802810709560000734"
    company_director_name: str = "Анищенко Сергей Сергеевич"
    company_director_position: str = "Индивидуальный предприниматель"

    # Templates
    templates_dir: Path = Path(__file__).parent.parent.parent / "templates"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
