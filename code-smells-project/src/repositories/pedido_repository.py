"""Order repository — single-JOIN listing eliminates N+1 (PB12)."""
from src.database import get_db


def insert_pedido(usuario_id: int, status: str, total: float) -> int:
    cur = get_db().cursor()
    cur.execute(
        "INSERT INTO pedidos (usuario_id, status, total) VALUES (?, ?, ?)",
        (usuario_id, status, total),
    )
    return cur.lastrowid


def insert_item(
    pedido_id: int, produto_id: int, quantidade: int, preco_unitario: float
) -> None:
    cur = get_db().cursor()
    cur.execute(
        "INSERT INTO itens_pedido (pedido_id, produto_id, quantidade, preco_unitario) "
        "VALUES (?, ?, ?, ?)",
        (pedido_id, produto_id, quantidade, preco_unitario),
    )


def update_status(pedido_id: int, novo_status: str) -> int:
    db = get_db()
    cur = db.cursor()
    cur.execute(
        "UPDATE pedidos SET status = ? WHERE id = ?", (novo_status, pedido_id)
    )
    db.commit()
    return cur.rowcount


def _rows_to_pedidos(rows) -> list[dict]:
    """Group flat JOIN rows by pedido id."""
    pedidos: dict[int, dict] = {}
    for r in rows:
        pid = r["pedido_id"]
        if pid not in pedidos:
            pedidos[pid] = {
                "id": pid,
                "usuario_id": r["usuario_id"],
                "status": r["status"],
                "total": r["total"],
                "criado_em": r["criado_em"],
                "itens": [],
            }
        if r["item_produto_id"] is not None:
            pedidos[pid]["itens"].append(
                {
                    "produto_id": r["item_produto_id"],
                    "produto_nome": r["produto_nome"] or "Desconhecido",
                    "quantidade": r["quantidade"],
                    "preco_unitario": r["preco_unitario"],
                }
            )
    return list(pedidos.values())


_LIST_QUERY = """
    SELECT
        p.id AS pedido_id,
        p.usuario_id,
        p.status,
        p.total,
        p.criado_em,
        ip.produto_id AS item_produto_id,
        ip.quantidade,
        ip.preco_unitario,
        pr.nome AS produto_nome
    FROM pedidos p
    LEFT JOIN itens_pedido ip ON ip.pedido_id = p.id
    LEFT JOIN produtos pr ON pr.id = ip.produto_id
"""


def list_by_user(usuario_id: int, limit: int, offset: int) -> list[dict]:
    cur = get_db().cursor()
    cur.execute(
        f"""
        {_LIST_QUERY}
        WHERE p.id IN (
            SELECT id FROM pedidos WHERE usuario_id = ?
            ORDER BY id LIMIT ? OFFSET ?
        )
        ORDER BY p.id
        """,
        (usuario_id, limit, offset),
    )
    return _rows_to_pedidos(cur.fetchall())


def list_all(limit: int, offset: int) -> list[dict]:
    cur = get_db().cursor()
    cur.execute(
        f"""
        {_LIST_QUERY}
        WHERE p.id IN (
            SELECT id FROM pedidos ORDER BY id LIMIT ? OFFSET ?
        )
        ORDER BY p.id
        """,
        (limit, offset),
    )
    return _rows_to_pedidos(cur.fetchall())


def count_all() -> int:
    cur = get_db().cursor()
    cur.execute("SELECT COUNT(*) FROM pedidos")
    return cur.fetchone()[0]


def count_by_user(usuario_id: int) -> int:
    cur = get_db().cursor()
    cur.execute("SELECT COUNT(*) FROM pedidos WHERE usuario_id = ?", (usuario_id,))
    return cur.fetchone()[0]


def aggregate_report() -> dict:
    cur = get_db().cursor()
    cur.execute(
        """
        SELECT
            COUNT(*) AS total,
            COALESCE(SUM(total), 0) AS faturamento,
            COALESCE(SUM(CASE WHEN status = 'pendente'  THEN 1 ELSE 0 END), 0) AS pendentes,
            COALESCE(SUM(CASE WHEN status = 'aprovado'  THEN 1 ELSE 0 END), 0) AS aprovados,
            COALESCE(SUM(CASE WHEN status = 'cancelado' THEN 1 ELSE 0 END), 0) AS cancelados
        FROM pedidos
        """
    )
    r = cur.fetchone()
    return {
        "total": r["total"],
        "faturamento": r["faturamento"],
        "pendentes": r["pendentes"],
        "aprovados": r["aprovados"],
        "cancelados": r["cancelados"],
    }


def reset_all() -> None:
    db = get_db()
    cur = db.cursor()
    cur.execute("DELETE FROM itens_pedido")
    cur.execute("DELETE FROM pedidos")
    cur.execute("DELETE FROM produtos")
    cur.execute("DELETE FROM usuarios")
    db.commit()
