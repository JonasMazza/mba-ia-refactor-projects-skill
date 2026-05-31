"""Product HTTP routes — thin handlers that delegate to the service layer."""
from flask import Blueprint, jsonify, request

from src.middlewares.auth import requires_auth
from src.routes._pagination import get_page_limit_offset
from src.services import produto_service

produto_bp = Blueprint("produtos", __name__)


@produto_bp.get("/produtos")
def listar_produtos():
    page, limit, offset = get_page_limit_offset()
    result = produto_service.list_produtos(limit, offset)
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


@produto_bp.get("/produtos/busca")
def buscar_produtos():
    page, limit, offset = get_page_limit_offset()
    termo = request.args.get("q", "") or None
    categoria = request.args.get("categoria") or None
    preco_min = request.args.get("preco_min")
    preco_max = request.args.get("preco_max")
    try:
        preco_min = float(preco_min) if preco_min else None
        preco_max = float(preco_max) if preco_max else None
    except ValueError:
        from src.middlewares.errors import ValidationError

        raise ValidationError("preco_min/preco_max devem ser numéricos")
    resultados = produto_service.buscar_produtos(
        termo, categoria, preco_min, preco_max, limit, offset
    )
    return (
        jsonify(
            {
                "dados": resultados,
                "total": len(resultados),
                "page": page,
                "limit": limit,
                "sucesso": True,
            }
        ),
        200,
    )


@produto_bp.get("/produtos/<int:produto_id>")
def buscar_produto(produto_id: int):
    produto = produto_service.get_produto(produto_id)
    return jsonify({"dados": produto, "sucesso": True}), 200


@produto_bp.post("/produtos")
@requires_auth(role="admin")
def criar_produto():
    new_id = produto_service.create_produto(request.get_json(silent=True))
    return (
        jsonify(
            {"dados": {"id": new_id}, "sucesso": True, "mensagem": "Produto criado"}
        ),
        201,
    )


@produto_bp.put("/produtos/<int:produto_id>")
@requires_auth(role="admin")
def atualizar_produto(produto_id: int):
    produto_service.update_produto(produto_id, request.get_json(silent=True))
    return jsonify({"sucesso": True, "mensagem": "Produto atualizado"}), 200


@produto_bp.delete("/produtos/<int:produto_id>")
@requires_auth(role="admin")
def deletar_produto(produto_id: int):
    produto_service.delete_produto(produto_id)
    return jsonify({"sucesso": True, "mensagem": "Produto deletado"}), 200
