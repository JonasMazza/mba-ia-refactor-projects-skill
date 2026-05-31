"""Product business logic."""
from src.middlewares.errors import NotFoundError
from src.repositories import produto_repository
from src.schemas.produto_schema import validate_produto


def list_produtos(limit: int, offset: int) -> dict:
    return {
        "items": produto_repository.list_all(limit, offset),
        "total": produto_repository.count_all(),
    }


def get_produto(produto_id: int) -> dict:
    produto = produto_repository.get_by_id(produto_id)
    if not produto:
        raise NotFoundError("produto não encontrado")
    return produto


def create_produto(dados: dict) -> int:
    payload = validate_produto(dados)
    return produto_repository.insert(
        payload["nome"],
        payload["descricao"],
        payload["preco"],
        payload["estoque"],
        payload["categoria"],
    )


def update_produto(produto_id: int, dados: dict) -> None:
    existing = produto_repository.get_by_id(produto_id)
    if not existing:
        raise NotFoundError("produto não encontrado")
    payload = validate_produto(dados)
    produto_repository.update(
        produto_id,
        payload["nome"],
        payload["descricao"],
        payload["preco"],
        payload["estoque"],
        payload["categoria"],
    )


def delete_produto(produto_id: int) -> None:
    existing = produto_repository.get_by_id(produto_id)
    if not existing:
        raise NotFoundError("produto não encontrado")
    produto_repository.delete(produto_id)


def buscar_produtos(
    termo: str | None,
    categoria: str | None,
    preco_min: float | None,
    preco_max: float | None,
    limit: int,
    offset: int,
) -> list[dict]:
    return produto_repository.search(
        termo, categoria, preco_min, preco_max, limit, offset
    )
