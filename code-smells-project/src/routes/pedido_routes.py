"""Order HTTP routes."""
from flask import Blueprint, jsonify, request

from src.middlewares.auth import requires_auth
from src.routes._pagination import get_page_limit_offset
from src.schemas.pedido_schema import validate_criar_pedido, validate_status
from src.services import pedido_service

pedido_bp = Blueprint("pedidos", __name__)


@pedido_bp.post("/pedidos")
@requires_auth()
def criar_pedido():
    payload = validate_criar_pedido(request.get_json(silent=True))
    result = pedido_service.create_pedido(payload["usuario_id"], payload["itens"])
    return (
        jsonify(
            {
                "dados": result,
                "sucesso": True,
                "mensagem": "Pedido criado com sucesso",
            }
        ),
        201,
    )


@pedido_bp.get("/pedidos")
@requires_auth(role="admin")
def listar_todos_pedidos():
    page, limit, offset = get_page_limit_offset()
    result = pedido_service.list_all(limit, offset)
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


@pedido_bp.get("/pedidos/usuario/<int:usuario_id>")
@requires_auth()
def listar_pedidos_usuario(usuario_id: int):
    page, limit, offset = get_page_limit_offset()
    result = pedido_service.list_by_user(usuario_id, limit, offset)
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


@pedido_bp.put("/pedidos/<int:pedido_id>/status")
@requires_auth(role="admin")
def atualizar_status_pedido(pedido_id: int):
    novo_status = validate_status(request.get_json(silent=True))
    pedido_service.update_status(pedido_id, novo_status)
    return jsonify({"sucesso": True, "mensagem": "Status atualizado"}), 200
