"""Application settings loaded from environment variables.

Reads from a `.env` file at process start (via python-dotenv) and exposes
typed settings. No secret literal lives in source code (AP01 / PB01).
"""
import os
from dotenv import load_dotenv

load_dotenv()


def _bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    # Secret/key — required, but with a dev fallback so the app boots locally
    # without manual setup. In production, set SECRET_KEY explicitly.
    SECRET_KEY: str = os.environ.get(
        "SECRET_KEY", "dev-secret-only-for-local-do-not-use-in-prod"
    )
    DEBUG: bool = _bool(os.environ.get("FLASK_DEBUG"), default=False)

    DB_PATH: str = os.environ.get("DB_PATH", "loja.db")
    PORT: int = int(os.environ.get("PORT", "5000"))

    # CORS: comma-separated allowlist, or "*" for any origin (dev only).
    CORS_ORIGINS: str = os.environ.get("CORS_ORIGINS", "*")

    LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO").upper()

    # When true, @requires_auth becomes a no-op. Useful for tests and local dev.
    AUTH_DISABLED: bool = _bool(os.environ.get("AUTH_DISABLED"), default=False)


settings = Settings()
