"""Domain exceptions + centralized error handler (PB15 — addresses AP15)."""
import logging

from flask import Flask, jsonify

log = logging.getLogger(__name__)


class AppError(Exception):
    status: int = 500

    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        if status is not None:
            self.status = status


class ValidationError(AppError):
    status = 400


class NotFoundError(AppError):
    status = 404


class AuthError(AppError):
    status = 401


class ForbiddenError(AppError):
    status = 403


class ConflictError(AppError):
    status = 409


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(AppError)
    def _handle_app_error(e: AppError):
        return jsonify({"erro": str(e), "sucesso": False}), e.status

    @app.errorhandler(404)
    def _handle_404(_e):
        return jsonify({"erro": "not found", "sucesso": False}), 404

    @app.errorhandler(405)
    def _handle_405(_e):
        return jsonify({"erro": "method not allowed", "sucesso": False}), 405

    @app.errorhandler(Exception)
    def _handle_unexpected(e: Exception):
        log.exception("unhandled exception")
        return (
            jsonify({"erro": "internal server error", "sucesso": False}),
            500,
        )
