"""Centralized error handlers.

Routes raise domain exceptions; this module translates them to HTTP
status codes with consistent JSON shape. Unexpected exceptions become
500 with a generic message (the traceback is logged, not returned).
"""
import logging

from flask import jsonify

logger = logging.getLogger(__name__)


class AppError(Exception):
    status = 500
    message = "internal error"

    def __init__(self, message: str | None = None, status: int | None = None):
        super().__init__(message or self.message)
        if message:
            self.message = message
        if status:
            self.status = status


class ValidationError(AppError):
    status = 400
    message = "validation error"


class NotFoundError(AppError):
    status = 404
    message = "not found"


class ConflictError(AppError):
    status = 409
    message = "conflict"


class AuthError(AppError):
    status = 401
    message = "unauthorized"


def register_error_handlers(app):
    @app.errorhandler(AppError)
    def handle_app_error(err: AppError):
        return jsonify({"error": err.message}), err.status

    @app.errorhandler(404)
    def handle_not_found(err):
        return jsonify({"error": "not found"}), 404

    @app.errorhandler(405)
    def handle_method_not_allowed(err):
        return jsonify({"error": "method not allowed"}), 405

    @app.errorhandler(Exception)
    def handle_unexpected(err):
        # Log full traceback but don't leak it to the client.
        logger.exception("Unhandled exception")
        return jsonify({"error": "internal server error"}), 500
