"""Database bootstrap (PB10 — request-scoped connection via flask.g).

Eliminates the global `db_connection` singleton (AP10).
"""
import sqlite3
import logging

from flask import g

from src.config.settings import settings
from src.services.auth_service import hash_password

log = logging.getLogger(__name__)


def get_db() -> sqlite3.Connection:
    """Return a per-request sqlite connection, opening one if needed."""
    if "db" not in g:
        conn = sqlite3.connect(settings.DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        g.db = conn
    return g.db


def close_db(_exception=None) -> None:
    db: sqlite3.Connection | None = g.pop("db", None)
    if db is not None:
        db.close()


def _create_schema(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            descricao TEXT,
            preco REAL,
            estoque INTEGER,
            categoria TEXT,
            ativo INTEGER DEFAULT 1,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            email TEXT UNIQUE,
            senha TEXT,
            tipo TEXT DEFAULT 'cliente',
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS pedidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            status TEXT DEFAULT 'pendente',
            total REAL,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS itens_pedido (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pedido_id INTEGER,
            produto_id INTEGER,
            quantidade INTEGER,
            preco_unitario REAL
        )
        """
    )
    conn.commit()


def _seed_if_empty(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM produtos")
    if cur.fetchone()[0] == 0:
        produtos = [
            ("Notebook Gamer", "Notebook potente para jogos", 5999.99, 10, "informatica"),
            ("Mouse Wireless", "Mouse sem fio ergonômico", 89.90, 50, "informatica"),
            ("Teclado Mecânico", "Teclado mecânico RGB", 299.90, 30, "informatica"),
            ("Monitor 27''", "Monitor 27 polegadas 144hz", 1899.90, 15, "informatica"),
            ("Headset Gamer", "Headset com microfone", 199.90, 25, "informatica"),
            ("Cadeira Gamer", "Cadeira ergonômica", 1299.90, 8, "moveis"),
            ("Webcam HD", "Webcam 1080p", 249.90, 20, "informatica"),
            ("Hub USB", "Hub USB 3.0 7 portas", 79.90, 40, "informatica"),
            ("SSD 1TB", "SSD NVMe 1TB", 449.90, 35, "informatica"),
            ("Camiseta Dev", "Camiseta estampa código", 59.90, 100, "vestuario"),
        ]
        cur.executemany(
            "INSERT INTO produtos (nome, descricao, preco, estoque, categoria) VALUES (?, ?, ?, ?, ?)",
            produtos,
        )

    cur.execute("SELECT COUNT(*) FROM usuarios")
    if cur.fetchone()[0] == 0:
        # Hash passwords on seed (PB04 — addresses AP04).
        usuarios = [
            ("Admin", "admin@loja.com", hash_password("admin123"), "admin"),
            ("João Silva", "joao@email.com", hash_password("123456"), "cliente"),
            ("Maria Santos", "maria@email.com", hash_password("senha123"), "cliente"),
        ]
        cur.executemany(
            "INSERT INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, ?)",
            usuarios,
        )
    conn.commit()


def init_db() -> None:
    """Create the schema and seed initial data. Called once at boot."""
    conn = sqlite3.connect(settings.DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        _create_schema(conn)
        _seed_if_empty(conn)
        log.info("database.initialized path=%s", settings.DB_PATH)
    finally:
        conn.close()
