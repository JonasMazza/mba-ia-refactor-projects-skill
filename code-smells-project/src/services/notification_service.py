"""Notification side-effects (replaces print() in controllers — AP07).

Currently a no-op/log adapter. Real implementations (email/SMS/push) can
swap in without touching controllers or order_service.
"""
import logging

log = logging.getLogger(__name__)


def notify_pedido_criado(pedido_id: int, usuario_id: int) -> None:
    log.info("notify.pedido_criado pedido_id=%s user_id=%s", pedido_id, usuario_id)


def notify_pedido_status(pedido_id: int, status: str) -> None:
    log.info("notify.pedido_status pedido_id=%s status=%s", pedido_id, status)
