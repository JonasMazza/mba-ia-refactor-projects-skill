"""Single-source product payload validation (PB13 — addresses AP13)."""
from src.constants import CATEGORIAS_VALIDAS, PRODUTO_NOME_MAX, PRODUTO_NOME_MIN
from src.middlewares.errors import ValidationError


def _require(dados: dict, field: str):
    if field not in dados or dados[field] is None or dados[field] == "":
        raise ValidationError(f"{field} é obrigatório")
    return dados[field]


def validate_produto(dados: dict | None, *, partial: bool = False) -> dict:
    if not dados:
        raise ValidationError("dados inválidos")

    if partial:
        nome = dados.get("nome")
        preco = dados.get("preco")
        estoque = dados.get("estoque")
    else:
        nome = _require(dados, "nome")
        preco = _require(dados, "preco")
        estoque = _require(dados, "estoque")

    descricao = dados.get("descricao", "")
    categoria = dados.get("categoria", "geral")

    if nome is not None:
        if not isinstance(nome, str):
            raise ValidationError("nome deve ser string")
        if len(nome) < PRODUTO_NOME_MIN:
            raise ValidationError("nome muito curto")
        if len(nome) > PRODUTO_NOME_MAX:
            raise ValidationError("nome muito longo")
    if preco is not None:
        if not isinstance(preco, (int, float)) or isinstance(preco, bool):
            raise ValidationError("preço deve ser numérico")
        if preco < 0:
            raise ValidationError("preço não pode ser negativo")
    if estoque is not None:
        if not isinstance(estoque, int) or isinstance(estoque, bool):
            raise ValidationError("estoque deve ser inteiro")
        if estoque < 0:
            raise ValidationError("estoque não pode ser negativo")
    if categoria not in CATEGORIAS_VALIDAS:
        raise ValidationError(
            f"categoria inválida. válidas: {list(CATEGORIAS_VALIDAS)}"
        )

    return {
        "nome": nome,
        "descricao": descricao,
        "preco": preco,
        "estoque": estoque,
        "categoria": categoria,
    }
