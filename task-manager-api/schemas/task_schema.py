"""Validation + parsing for Task payloads.

Light-touch helpers — kept dependency-free (no marshmallow) to keep the
diff narrow and behaviour identical to the legacy inline validation.
The single source of truth for valid values lives in `schemas.constants`.
"""
from datetime import datetime

from middlewares.error_handler import ValidationError
from schemas.constants import (
    MAX_PRIORITY,
    MAX_TITLE_LENGTH,
    MIN_PRIORITY,
    MIN_TITLE_LENGTH,
    VALID_STATUSES,
)


def _parse_due_date(raw):
    if raw is None or raw == "":
        return None
    if isinstance(raw, datetime):
        return raw
    try:
        return datetime.strptime(raw, "%Y-%m-%d")
    except (ValueError, TypeError):
        raise ValidationError("Formato de data inválido. Use YYYY-MM-DD")


def _normalize_tags(raw):
    if raw is None:
        return None
    if isinstance(raw, list):
        return ",".join(str(t) for t in raw)
    return str(raw)


def validate_title(title: str | None, *, required: bool):
    if title is None:
        if required:
            raise ValidationError("Título é obrigatório")
        return None
    if not isinstance(title, str):
        raise ValidationError("Título inválido")
    if len(title) < MIN_TITLE_LENGTH:
        raise ValidationError("Título muito curto")
    if len(title) > MAX_TITLE_LENGTH:
        raise ValidationError("Título muito longo")
    return title


def validate_status(status):
    if status is None:
        return None
    if status not in VALID_STATUSES:
        raise ValidationError("Status inválido")
    return status


def validate_priority(priority):
    if priority is None:
        return None
    try:
        p = int(priority)
    except (TypeError, ValueError):
        raise ValidationError("Prioridade inválida")
    if p < MIN_PRIORITY or p > MAX_PRIORITY:
        raise ValidationError(f"Prioridade deve ser entre {MIN_PRIORITY} e {MAX_PRIORITY}")
    return p


def parse_create(data: dict) -> dict:
    """Validate + normalize a POST /tasks payload."""
    if not isinstance(data, dict):
        raise ValidationError("Dados inválidos")

    return {
        "title": validate_title(data.get("title"), required=True),
        "description": data.get("description", "") or "",
        "status": validate_status(data.get("status")) or "pending",
        "priority": validate_priority(data.get("priority")) or 3,
        "user_id": data.get("user_id"),
        "category_id": data.get("category_id"),
        "due_date": _parse_due_date(data.get("due_date")),
        "tags": _normalize_tags(data.get("tags")),
    }


def parse_update(data: dict) -> dict:
    """Validate + normalize a PUT /tasks/<id> payload (partial)."""
    if not isinstance(data, dict):
        raise ValidationError("Dados inválidos")

    out: dict = {}
    if "title" in data:
        out["title"] = validate_title(data["title"], required=False)
    if "description" in data:
        out["description"] = data["description"]
    if "status" in data:
        out["status"] = validate_status(data["status"])
        if out["status"] is None:
            raise ValidationError("Status inválido")
    if "priority" in data:
        out["priority"] = validate_priority(data["priority"])
        if out["priority"] is None:
            raise ValidationError("Prioridade inválida")
    if "user_id" in data:
        out["user_id"] = data["user_id"]
    if "category_id" in data:
        out["category_id"] = data["category_id"]
    if "due_date" in data:
        out["due_date"] = _parse_due_date(data["due_date"])
    if "tags" in data:
        out["tags"] = _normalize_tags(data["tags"])
    return out
