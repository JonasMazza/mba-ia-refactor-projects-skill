"""Product repository — all SQL is parameterized (PB03)."""
from src.database import get_db


PRODUTO_COLUMNS = (
    "id",
    "nome",
    "descricao",
    "preco",
    "estoque",
    "categoria",
    "ativo",
    "criado_em",
)


def _row_to_dict(row) -> dict:
    return {c: row[c] for c in PRODUTO_COLUMNS}


def list_all(limit: int, offset: int) -> list[dict]:
    cur = get_db().cursor()
    cur.execute(
        "SELECT * FROM produtos ORDER BY id LIMIT ? OFFSET ?", (limit, offset)
    )
    return [_row_to_dict(r) for r in cur.fetchall()]


def count_all() -> int:
    cur = get_db().cursor()
    cur.execute("SELECT COUNT(*) FROM produtos")
    return cur.fetchone()[0]


def get_by_id(produto_id: int) -> dict | None:
    cur = get_db().cursor()
    cur.execute("SELECT * FROM produtos WHERE id = ?", (produto_id,))
    row = cur.fetchone()
    return _row_to_dict(row) if row else None


def insert(
    nome: str, descricao: str, preco: float, estoque: int, categoria: str
) -> int:
    db = get_db()
    cur = db.cursor()
    cur.execute(
        "INSERT INTO produtos (nome, descricao, preco, estoque, categoria) "
        "VALUES (?, ?, ?, ?, ?)",
        (nome, descricao, preco, estoque, categoria),
    )
    db.commit()
    return cur.lastrowid


def update(
    produto_id: int,
    nome: str,
    descricao: str,
    preco: float,
    estoque: int,
    categoria: str,
) -> None:
    db = get_db()
    cur = db.cursor()
    cur.execute(
        "UPDATE produtos SET nome = ?, descricao = ?, preco = ?, "
        "estoque = ?, categoria = ? WHERE id = ?",
        (nome, descricao, preco, estoque, categoria, produto_id),
    )
    db.commit()


def delete(produto_id: int) -> None:
    db = get_db()
    cur = db.cursor()
    cur.execute("DELETE FROM produtos WHERE id = ?", (produto_id,))
    db.commit()


def search(
    termo: str | None,
    categoria: str | None,
    preco_min: float | None,
    preco_max: float | None,
    limit: int,
    offset: int,
) -> list[dict]:
    """Dynamic filter, but every fragment uses placeholders (PB03)."""
    parts = ["SELECT * FROM produtos WHERE 1=1"]
    params: list = []
    if termo:
        parts.append("AND (nome LIKE ? OR descricao LIKE ?)")
        like = f"%{termo}%"
        params.extend([like, like])
    if categoria:
        parts.append("AND categoria = ?")
        params.append(categoria)
    if preco_min is not None:
        parts.append("AND preco >= ?")
        params.append(preco_min)
    if preco_max is not None:
        parts.append("AND preco <= ?")
        params.append(preco_max)
    parts.append("ORDER BY id LIMIT ? OFFSET ?")
    params.extend([limit, offset])

    cur = get_db().cursor()
    cur.execute(" ".join(parts), params)
    return [_row_to_dict(r) for r in cur.fetchall()]


def decrement_stock(produto_id: int, quantidade: int) -> int:
    """Conditional UPDATE — returns affected rowcount.

    Lets the service detect concurrent oversell (PB08).
    """
    cur = get_db().cursor()
    cur.execute(
        "UPDATE produtos SET estoque = estoque - ? "
        "WHERE id = ? AND estoque >= ?",
        (quantidade, produto_id, quantidade),
    )
    return cur.rowcount
