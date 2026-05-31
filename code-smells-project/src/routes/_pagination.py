"""Pagination helpers (PB17)."""
from flask import request

from src.constants import PAGINATION_DEFAULT_LIMIT, PAGINATION_MAX_LIMIT
from src.middlewares.errors import ValidationError


def get_page_limit_offset() -> tuple[int, int, int]:
    try:
        page = max(1, int(request.args.get("page", 1)))
        limit = int(request.args.get("limit", PAGINATION_DEFAULT_LIMIT))
    except (TypeError, ValueError):
        raise ValidationError("page/limit devem ser inteiros")
    limit = max(1, min(PAGINATION_MAX_LIMIT, limit))
    offset = (page - 1) * limit
    return page, limit, offset
