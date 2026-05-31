"""JWT-based auth decorator (PB02 — addresses AP02).

Set AUTH_DISABLED=true in the environment to bypass auth for local dev/test.
That toggle is intentional: validation curls and quick smoke tests don't
need a real token, but production must set AUTH_DISABLED=false (default).
"""
from functools import wraps

import jwt
from flask import g, request

from src.config.settings import settings
from src.middlewares.errors import AuthError, ForbiddenError


def _decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise AuthError("token inválido") from exc


def requires_auth(role: str | None = None):
    """Decorator that enforces a valid JWT in the Authorization header.

    If `role` is given, the token payload must have a matching `role` claim.
    """

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if settings.AUTH_DISABLED:
                # Dev/test escape hatch — see module docstring.
                g.current_user = {"id": None, "role": role or "admin"}
                return fn(*args, **kwargs)

            header = request.headers.get("Authorization", "")
            if not header.startswith("Bearer "):
                raise AuthError("token ausente")
            payload = _decode_token(header[len("Bearer ") :])
            if role and payload.get("role") != role:
                raise ForbiddenError("permissão insuficiente")
            g.current_user = payload
            return fn(*args, **kwargs)

        return wrapper

    return decorator
