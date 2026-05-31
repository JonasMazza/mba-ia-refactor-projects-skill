"""Password hashing + login (PB04 — bcrypt).

Kept dependency-free of `database.py` to avoid circular imports during
seed (database.py imports `hash_password` from this module).
"""
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(rounds=12)).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except (ValueError, TypeError):
        return False


def issue_token(user_id: int, role: str, secret_key: str, ttl_minutes: int = 60) -> str:
    payload = {
        "sub": user_id,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, secret_key, algorithm="HS256")
