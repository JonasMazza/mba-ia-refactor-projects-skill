"""User & auth HTTP routes."""
from flask import Blueprint, jsonify, request

from src.middlewares.auth import requires_auth
from src.routes._pagination import get_page_limit_offset
from src.schemas.usuario_schema import validate_login, validate_signup
from src.services import usuario_service

usuario_bp = Blueprint("usuarios", __name__)


@usuario_bp.get("/usuarios")
@requires_auth(role="admin")
def listar_usuarios():
    page, limit, offset = get_page_limit_offset()
    result = usuario_service.list_usuarios(limit, offset)
    return (
        jsonify(
            {
                "dados": result["items"],
                "total": result["total"],
                "page": page,
                "limit": limit,
                "sucesso": True,
            }
        ),
        200,
    )


@usuario_bp.get("/usuarios/<int:usuario_id>")
@requires_auth()
def buscar_usuario(usuario_id: int):
    usuario = usuario_service.get_usuario(usuario_id)
    return jsonify({"dados": usuario, "sucesso": True}), 200


@usuario_bp.post("/usuarios")
def criar_usuario():
    payload = validate_signup(request.get_json(silent=True))
    new_id = usuario_service.create_usuario(payload)
    return jsonify({"dados": {"id": new_id}, "sucesso": True}), 201


@usuario_bp.post("/login")
def login():
    payload = validate_login(request.get_json(silent=True))
    result = usuario_service.login(payload)
    return (
        jsonify({"dados": result, "sucesso": True, "mensagem": "Login OK"}),
        200,
    )
