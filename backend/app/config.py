from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Student Academic Management System"
    database_url: str = "sqlite:///./sams.db"

    secret_key: str = "dev-secret-change-me"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    # Optional regex allow-list, e.g. r"https://.*\.example\.com" for hosted frontends.
    cors_origin_regex: str | None = None

    # Directory containing a built frontend bundle. When set, the SPA is served
    # from the same origin as the API.
    static_dir: str | None = None

    # When true the demo dataset is created on startup if the database is empty.
    # Intended for demo/staging deployments only.
    seed_demo_data: bool = False

    # Optional LLM configuration. When unset the system falls back to the
    # deterministic rule-based insight generator.
    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"

    # Thresholds used by the analytics layer.
    attendance_risk_threshold: float = 75.0
    marks_risk_threshold: float = 40.0
    marks_decline_threshold: float = 10.0

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
