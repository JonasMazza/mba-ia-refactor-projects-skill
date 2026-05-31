"""Validation for Category payloads."""
from middlewares.error_handler import ValidationError
from schemas.constants import DEFAULT_COLOR


def _validate_color(color):
    if color is None:
        return DEFAULT_COLOR
    if not isinstance(color, str) or len(color) != 7 or not color.startswith("#"):
        raise ValidationError("Cor inválida (use formato #RRGGBB)")
    return color


def parse_create(data: dict) -> dict:
    if not isinstance(data, dict):
        raise ValidationError("Dados inválidos")
    name = data.get("name")
    if not name:
        raise ValidationError("Nome é obrigatório")
    return {
        "name": name,
        "description": data.get("description", "") or "",
        "color": _validate_color(data.get("color")),
    }


def parse_update(data: dict) -> dict:
    if not isinstance(data, dict):
        raise ValidationError("Dados inválidos")
    out: dict = {}
    if "name" in data:
        out["name"] = data["name"]
    if "description" in data:
        out["description"] = data["description"]
    if "color" in data:
        out["color"] = _validate_color(data["color"])
    return out
