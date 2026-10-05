"""Application settings, read from environment variables (and the .env file).

If a required variable is missing (for example SECRET_KEY), the app refuses to start
and Pydantic prints which one is missing (HU-00).
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "Brava API"
    environment: str = "local"
    debug: bool = False
    database_url: str = "sqlite:///./brava.db"

    # Required on purpose: no default value, so a missing secret stops the app.
    secret_key: str

    jwt_algorithm: str = "HS256"
    jwt_issuer: str = "brava-api"
    jwt_audience: str = "brava-web"
    access_token_expire_minutes: int = 60

    # Only the frontend origin may call the API from a browser (never "*").
    cors_origins: list[str] = ["http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    """Return the settings once and reuse them (cached)."""
    return Settings()
