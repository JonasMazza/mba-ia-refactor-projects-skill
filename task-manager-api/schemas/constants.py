"""Domain constants — single source of truth."""

VALID_STATUSES = ["pending", "in_progress", "done", "cancelled"]
VALID_ROLES = ["user", "admin", "manager"]

MIN_TITLE_LENGTH = 3
MAX_TITLE_LENGTH = 200
MIN_PASSWORD_LENGTH = 4
DEFAULT_PRIORITY = 3
MIN_PRIORITY = 1
MAX_PRIORITY = 5
DEFAULT_COLOR = "#000000"
EMAIL_REGEX = r"^[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+$"

# Pagination defaults
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
