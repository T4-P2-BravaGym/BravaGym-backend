from functools import lru_cache
from pathlib import Path

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

    # Public list cache for /plans and /products (HU-28). Seconds until expiry.
    cache_ttl_seconds: int = 60

    # Auth attempt windows (HU-34). In-memory only — single process.
    auth_login_max_attempts: int = 5
    auth_login_window_seconds: int = 900
    auth_register_max_attempts: int = 10
    auth_register_window_seconds: int = 3600

    # Uploaded files (HU-30), relative to where uvicorn starts (the repo root).
    media_root: Path = Path("media")

    # Stripe (HU-29). Empty / missing secret → simulated pay only (HU-24).
    stripe_secret_key: str | None = None
    stripe_publishable_key: str | None = None
    stripe_webhook_secret: str | None = None
    stripe_success_url: str = "http://localhost:5173/member/payments?stripe=success"
    stripe_cancel_url: str = "http://localhost:5173/member/payments?stripe=cancel"

    @property
    def stripe_enabled(self) -> bool:
        """True when a Stripe secret key is configured (test or live)."""
        return bool(self.stripe_secret_key and self.stripe_secret_key.strip())


@lru_cache
def get_settings() -> Settings:
    """Return the settings once and reuse them (cached)."""
    return Settings()
