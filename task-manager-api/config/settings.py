"""Centralized configuration loaded from environment variables.

All sensitive values (secrets, credentials, DB URLs) live here — never
in source. Use a `.env` file in dev (loaded via python-dotenv).
"""
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _env_list(name: str, default: list[str]) -> list[str]:
    raw = os.environ.get(name)
    if not raw:
        return default
    return [item.strip() for item in raw.split(",") if item.strip()]


class Settings:
    # Flask
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "dev-only-change-me-in-prod")
    DEBUG: bool = _env_bool("DEBUG", default=False)
    PORT: int = int(os.environ.get("PORT", "5000"))

    # Database
    DB_URL: str = os.environ.get("DB_URL", "sqlite:///tasks.db")

    # Auth
    JWT_ALGORITHM: str = os.environ.get("JWT_ALGORITHM", "HS256")
    JWT_EXP_HOURS: int = int(os.environ.get("JWT_EXP_HOURS", "24"))
    # Escape hatch for dev — when true, @requires_auth becomes a no-op so
    # validation curls can hit protected endpoints without minting a token.
    AUTH_DISABLED: bool = _env_bool("AUTH_DISABLED", default=False)

    # CORS — allowlist of origins; "*" only allowed when explicitly set
    CORS_ORIGINS: list[str] = _env_list(
        "CORS_ORIGINS",
        default=["http://localhost:3000", "http://localhost:5173"],
    )

    # SMTP (NotificationService)
    SMTP_HOST: str = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.environ.get("SMTP_PORT", "587"))
    SMTP_USER: str | None = os.environ.get("SMTP_USER")
    SMTP_PASSWORD: str | None = os.environ.get("SMTP_PASSWORD")
    # When false (default in dev), NotificationService logs instead of
    # actually trying to connect to SMTP.
    NOTIFICATIONS_ENABLED: bool = _env_bool("NOTIFICATIONS_ENABLED", default=False)


settings = Settings()
