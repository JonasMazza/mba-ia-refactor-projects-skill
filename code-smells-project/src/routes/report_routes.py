"""Sales report routes."""
from flask import Blueprint, jsonify

from src.middlewares.auth import requires_auth
from src.services import report_service

report_bp = Blueprint("relatorios", __name__)


@report_bp.get("/relatorios/vendas")
@requires_auth(role="admin")
def relatorio_vendas():
    relatorio = report_service.relatorio_vendas()
    return jsonify({"dados": relatorio, "sucesso": True}), 200
