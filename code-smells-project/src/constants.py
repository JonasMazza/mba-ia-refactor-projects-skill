"""Domain constants (AP19 / PB13)."""

CATEGORIAS_VALIDAS = (
    "informatica",
    "moveis",
    "vestuario",
    "geral",
    "eletronicos",
    "livros",
)

STATUS_PEDIDO_VALIDOS = (
    "pendente",
    "aprovado",
    "enviado",
    "entregue",
    "cancelado",
)

# Tiered discount on total revenue (used by report_service).
DISCOUNT_TIERS = (
    (10000, 0.10),
    (5000, 0.05),
    (1000, 0.02),
)

# Pagination defaults (PB17 / AP17).
PAGINATION_DEFAULT_LIMIT = 20
PAGINATION_MAX_LIMIT = 100

PRODUTO_NOME_MIN = 2
PRODUTO_NOME_MAX = 200
