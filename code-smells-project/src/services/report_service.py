"""Sales report — discount tier rules live here, not in repository (PB07)."""
from src.constants import DISCOUNT_TIERS
from src.repositories import pedido_repository


def _calculate_discount(faturamento: float) -> float:
    for threshold, rate in DISCOUNT_TIERS:
        if faturamento > threshold:
            return faturamento * rate
    return 0.0


def relatorio_vendas() -> dict:
    agg = pedido_repository.aggregate_report()
    faturamento = float(agg["faturamento"])
    total_pedidos = agg["total"]
    desconto = _calculate_discount(faturamento)
    ticket_medio = round(faturamento / total_pedidos, 2) if total_pedidos else 0
    return {
        "total_pedidos": total_pedidos,
        "faturamento_bruto": round(faturamento, 2),
        "desconto_aplicavel": round(desconto, 2),
        "faturamento_liquido": round(faturamento - desconto, 2),
        "pedidos_pendentes": agg["pendentes"],
        "pedidos_aprovados": agg["aprovados"],
        "pedidos_cancelados": agg["cancelados"],
        "ticket_medio": ticket_medio,
    }
