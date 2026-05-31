"""User business logic + login orchestration."""
import logging

from src.config.settings import settings
from src.middlewares.errors import (
    AuthError,
    ConflictError,
    NotFoundError,
)
from src.repositories import usuario_repository
from src.services.auth_service import hash_password, issue_token, verify_password

log = logging.getLogger(__name__)


def list_usuarios(limit: int, offset: int) -> dict:
    return {
        "items": usuario_repository.list_all(limit, offset),
        "total": usuario_repository.count_all(),
    }


def get_usuario(usuario_id: int) -> dict:
    usuario = usuario_repository.get_by_id(usuario_id)
    if not usuario:
        raise NotFoundError("usuário não encontrado")
    return usuario


def create_usuario(payload: dict) -> int:
    if usuario_repository.email_exists(payload["email"]):
        raise ConflictError("email já cadastrado")
    senha_hash = hash_password(payload["senha"])
    user_id = usuario_repository.insert(
        payload["nome"], payload["email"], senha_hash
    )
    log.info("usuario.created user_id=%s", user_id)
    return user_id


def login(payload: dict) -> dict:
    user = usuario_repository.get_with_password_by_email(payload["email"])
    if not user or not verify_password(payload["senha"], user["senha"]):
        log.warning("login.failed")  # no PII (AP05 / PB14)
        raise AuthError("email ou senha inválidos")

    token = issue_token(user["id"], user["tipo"], settings.SECRET_KEY)
    log.info("login.success user_id=%s", user["id"])
    return {
        "token": token,
        "usuario": {
            "id": user["id"],
            "nome": user["nome"],
            "email": user["email"],
            "tipo": user["tipo"],
        },
    }
