"""Order service — transactional create, status updates, listings (PB07/PB08)."""
import logging

from src.database import get_db
from src.middlewares.errors import ConflictError, NotFoundError, ValidationError
from src.repositories import pedido_repository, produto_repository
from src.services import notification_service

log = logging.getLogger(__name__)


def list_by_user(usuario_id: int, limit: int, offset: int) -> dict:
    return {
        "items": pedido_repository.list_by_user(usuario_id, limit, offset),
        "total": pedido_repository.count_by_user(usuario_id),
    }


def list_all(limit: int, offset: int) -> dict:
    return {
        "items": pedido_repository.list_all(limit, offset),
        "total": pedido_repository.count_all(),
    }


def create_pedido(usuario_id: int, itens: list[dict]) -> dict:
    """Atomic checkout with stock guard (PB08 — addresses AP08)."""
    db = get_db()

    produtos_cache: dict[int, dict] = {}
    total = 0.0
    for item in itens:
        produto = produto_repository.get_by_id(item["produto_id"])
        if produto is None:
            raise NotFoundError(f"produto {item['produto_id']} não encontrado")
        if produto["estoque"] < item["quantidade"]:
            raise ConflictError(f"estoque insuficiente para {produto['nome']}")
        produtos_cache[item["produto_id"]] = produto
        total += produto["preco"] * item["quantidade"]

    try:
        db.execute("BEGIN")
        pedido_id = pedido_repository.insert_pedido(usuario_id, "pendente", total)
        for item in itens:
            produto = produtos_cache[item["produto_id"]]
            affected = produto_repository.decrement_stock(
                item["produto_id"], item["quantidade"]
            )
            if affected == 0:
                # Concurrent oversell — roll back.
                raise ConflictError(
                    f"estoque insuficiente para {produto['nome']} "
                    "(condição de corrida)"
                )
            pedido_repository.insert_item(
                pedido_id,
                item["produto_id"],
                item["quantidade"],
                produto["preco"],
            )
        db.commit()
    except Exception:
        db.rollback()
        raise

    notification_service.notify_pedido_criado(pedido_id, usuario_id)
    return {"pedido_id": pedido_id, "total": round(total, 2)}


def update_status(pedido_id: int, novo_status: str) -> None:
    affected = pedido_repository.update_status(pedido_id, novo_status)
    if affected == 0:
        raise NotFoundError("pedido não encontrado")
    notification_service.notify_pedido_status(pedido_id, novo_status)


def reset_database() -> None:
    pedido_repository.reset_all()
    log.warning("admin.reset-db executed")
