"""System routes: index and health."""
from flask import Blueprint, jsonify

from src.database import get_db

system_bp = Blueprint("system", __name__)


@system_bp.get("/")
def index():
    return jsonify(
        {
            "mensagem": "Bem-vindo à API da Loja",
            "versao": "1.0.0",
            "endpoints": {
                "produtos": "/produtos",
                "usuarios": "/usuarios",
                "pedidos": "/pedidos",
                "login": "/login",
                "relatorios": "/relatorios/vendas",
                "health": "/health",
            },
        }
    )


@system_bp.get("/health")
def health_check():
    """Minimal health probe — no secrets, no PII, no schema info (AP05)."""
    try:
        cur = get_db().cursor()
        cur.execute("SELECT 1")
        cur.fetchone()
        return jsonify({"status": "ok"}), 200
    except Exception:
        return jsonify({"status": "error"}), 503
