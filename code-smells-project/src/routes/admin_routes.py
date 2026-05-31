"""Admin/destructive routes.

NOTE: the previous `/admin/query` endpoint (arbitrary SQL execution) was
REMOVED entirely per AP02 — there is no legitimate use case for sending
raw SQL over HTTP.
"""
from flask import Blueprint, jsonify

from src.middlewares.auth import requires_auth
from src.services import pedido_service

admin_bp = Blueprint("admin", __name__)


@admin_bp.post("/admin/reset-db")
@requires_auth(role="admin")
def reset_database():
    pedido_service.reset_database()
    return jsonify({"mensagem": "Banco de dados resetado", "sucesso": True}), 200
