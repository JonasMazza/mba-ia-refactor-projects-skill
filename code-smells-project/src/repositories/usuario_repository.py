"""User repository — parameterized SQL only (PB03)."""
from src.database import get_db


PUBLIC_FIELDS = ("id", "nome", "email", "tipo", "criado_em")


def _public(row) -> dict:
    """Allowlist serializer — never includes `senha` (PB05 / AP05)."""
    return {f: row[f] for f in PUBLIC_FIELDS}


def list_all(limit: int, offset: int) -> list[dict]:
    cur = get_db().cursor()
    cur.execute(
        "SELECT id, nome, email, tipo, criado_em FROM usuarios "
        "ORDER BY id LIMIT ? OFFSET ?",
        (limit, offset),
    )
    return [_public(r) for r in cur.fetchall()]


def count_all() -> int:
    cur = get_db().cursor()
    cur.execute("SELECT COUNT(*) FROM usuarios")
    return cur.fetchone()[0]


def get_by_id(usuario_id: int) -> dict | None:
    cur = get_db().cursor()
    cur.execute(
        "SELECT id, nome, email, tipo, criado_em FROM usuarios WHERE id = ?",
        (usuario_id,),
    )
    row = cur.fetchone()
    return _public(row) if row else None


def get_with_password_by_email(email: str) -> dict | None:
    """Return full row (incl. hashed password) for login flow only."""
    cur = get_db().cursor()
    cur.execute(
        "SELECT id, nome, email, senha, tipo FROM usuarios WHERE email = ?",
        (email,),
    )
    row = cur.fetchone()
    if not row:
        return None
    return {k: row[k] for k in ("id", "nome", "email", "senha", "tipo")}


def insert(nome: str, email: str, senha_hash: str, tipo: str = "cliente") -> int:
    db = get_db()
    cur = db.cursor()
    cur.execute(
        "INSERT INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, ?)",
        (nome, email, senha_hash, tipo),
    )
    db.commit()
    return cur.lastrowid


def email_exists(email: str) -> bool:
    cur = get_db().cursor()
    cur.execute("SELECT 1 FROM usuarios WHERE email = ?", (email,))
    return cur.fetchone() is not None
