"""Настройки приложения. Читаются из переменных окружения и backend/.env."""
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore")

    app_name: str = "Smart Orchid API"
    # SQLite для MVP. Для PostgreSQL: postgresql+psycopg://user:pass@host/db
    database_url: str = f"sqlite:///{BASE_DIR / 'smart_orchid.db'}"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # AI: ключ хранится только на сервере. auto = Claude, если ключ задан, иначе Demo.
    anthropic_api_key: str | None = None
    ai_mode: Literal["auto", "demo", "claude"] = "auto"
    claude_model: str = "claude-opus-5-5"
    claude_effort: Literal["low", "medium", "high", "xhigh", "max"] = "medium"

    # Демо-данные
    seed_on_startup: bool = True
    demo_history_days: int = 30
    demo_step_minutes: int = 30

    upload_dir: Path = BASE_DIR / "uploads"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def effective_ai_mode(self) -> Literal["demo", "claude"]:
        if self.ai_mode == "demo":
            return "demo"
        if self.anthropic_api_key:
            return "claude"
        return "demo"


@lru_cache
def get_settings() -> Settings:
    return Settings()
