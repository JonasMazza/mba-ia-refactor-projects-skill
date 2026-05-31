"""JWT auth decorator.

Use `@requires_auth()` to require any authenticated user, or
`@requires_auth(role='admin')` to require a specific role.

When `settings.AUTH_DISABLED` is true (dev escape hatch), the decorator
becomes a no-op and attaches a synthetic admin identity to the request.
"""
from functools import wraps

import jwt
from flask import request, jsonify, g

from config.settings import settings


class AuthError(Exception):
    def __init__(self, message: str, status: int = 401):
        super().__init__(message)
        self.status = status


def encode_token(user) -> str:
    from datetime import datetime, timezone, timedelta

    payload = {
        "sub": user.id,
        "role": user.role,
        "email": user.email,
        "exp": datetime.now(timezone.utc) + timedelta(hours=settings.JWT_EXP_HOURS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])


def requires_auth(role: str | None = None):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if settings.AUTH_DISABLED:
                g.current_user = {"sub": 0, "role": "admin", "email": "dev@local"}
                return fn(*args, **kwargs)

            auth_header = request.headers.get("Authorization", "")
            if not auth_header.startswith("Bearer "):
                return jsonify({"error": "missing or malformed Authorization header"}), 401

            token = auth_header[len("Bearer "):].strip()
            try:
                payload = decode_token(token)
            except jwt.ExpiredSignatureError:
                return jsonify({"error": "token expired"}), 401
            except jwt.PyJWTError:
                return jsonify({"error": "invalid token"}), 401

            if role and payload.get("role") != role:
                return jsonify({"error": "forbidden"}), 403

            g.current_user = payload
            return fn(*args, **kwargs)

        return wrapper

    return decorator
