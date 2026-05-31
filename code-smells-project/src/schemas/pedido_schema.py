"""Order payload validation."""
from src.constants import STATUS_PEDIDO_VALIDOS
from src.middlewares.errors import ValidationError


def validate_criar_pedido(dados: dict | None) -> dict:
    if not dados:
        raise ValidationError("dados inválidos")
    usuario_id = dados.get("usuario_id")
    itens = dados.get("itens") or []

    if not usuario_id or not isinstance(usuario_id, int):
        raise ValidationError("usuario_id é obrigatório (int)")
    if not isinstance(itens, list) or not itens:
        raise ValidationError("pedido deve ter pelo menos 1 item")

    normalized = []
    for raw in itens:
        if not isinstance(raw, dict):
            raise ValidationError("cada item deve ser um objeto")
        produto_id = raw.get("produto_id")
        quantidade = raw.get("quantidade")
        if not isinstance(produto_id, int) or produto_id <= 0:
            raise ValidationError("produto_id inválido")
        if not isinstance(quantidade, int) or quantidade <= 0:
            raise ValidationError("quantidade inválida")
        normalized.append({"produto_id": produto_id, "quantidade": quantidade})
    return {"usuario_id": usuario_id, "itens": normalized}


def validate_status(dados: dict | None) -> str:
    if not dados:
        raise ValidationError("dados inválidos")
    status = (dados.get("status") or "").strip()
    if status not in STATUS_PEDIDO_VALIDOS:
        raise ValidationError(
            f"status inválido. válidos: {list(STATUS_PEDIDO_VALIDOS)}"
        )
    return status
