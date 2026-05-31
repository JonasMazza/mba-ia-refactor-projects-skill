"""Validation + serialization for User payloads."""
import re

from middlewares.error_handler import ValidationError
from schemas.constants import EMAIL_REGEX, MIN_PASSWORD_LENGTH, VALID_ROLES


def _validate_email(email):
    if not isinstance(email, str) or not re.match(EMAIL_REGEX, email):
        raise ValidationError("Email inválido")
    return email


def _validate_password(pwd):
    if not isinstance(pwd, str) or len(pwd) < MIN_PASSWORD_LENGTH:
        raise ValidationError(f"Senha deve ter no mínimo {MIN_PASSWORD_LENGTH} caracteres")
    return pwd


def _validate_role(role):
    if role is None:
        return "user"
    if role not in VALID_ROLES:
        raise ValidationError("Role inválido")
    return role


def parse_create(data: dict) -> dict:
    if not isinstance(data, dict):
        raise ValidationError("Dados inválidos")

    name = data.get("name")
    if not name:
        raise ValidationError("Nome é obrigatório")

    email = data.get("email")
    if not email:
        raise ValidationError("Email é obrigatório")
    email = _validate_email(email)

    password = data.get("password")
    if not password:
        raise ValidationError("Senha é obrigatória")
    password = _validate_password(password)

    return {
        "name": name,
        "email": email,
        "password": password,
        "role": _validate_role(data.get("role")),
    }


def parse_update(data: dict) -> dict:
    if not isinstance(data, dict):
        raise ValidationError("Dados inválidos")
    out: dict = {}
    if "name" in data:
        out["name"] = data["name"]
    if "email" in data:
        out["email"] = _validate_email(data["email"])
    if "password" in data:
        out["password"] = _validate_password(data["password"])
    if "role" in data:
        out["role"] = _validate_role(data["role"])
    if "active" in data:
        out["active"] = bool(data["active"])
    return out


def public_dict(user) -> dict:
    """Serialize a User to JSON-safe dict — allowlist, never password."""
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "active": user.active,
        "created_at": str(user.created_at),
    }
