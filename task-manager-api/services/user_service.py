"""User domain service.

Centralizes user CRUD + login, replacing the previously fat user_routes.py.
Password handling delegates to `User.set_password` (bcrypt).
"""
from datetime import datetime, timezone

from sqlalchemy.orm import joinedload

from database import db
from middlewares.error_handler import (
    AuthError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from models.task import Task
from models.user import User
from schemas.user_schema import public_dict


def list_users(*, page: int = 1, per_page: int = 20) -> list[dict]:
    users = (
        User.query.options(joinedload(User.tasks))
        .order_by(User.id)
        .limit(per_page)
        .offset((page - 1) * per_page)
        .all()
    )
    result = []
    for u in users:
        data = public_dict(u)
        data["task_count"] = len(u.tasks)
        result.append(data)
    return result


def get_user(user_id: int) -> dict:
    user = db.session.get(User, user_id)
    if not user:
        raise NotFoundError("Usuário não encontrado")
    data = public_dict(user)
    tasks = Task.query.filter_by(user_id=user_id).all()
    data["tasks"] = [t.to_dict() for t in tasks]
    return data


def create_user(payload: dict) -> dict:
    if User.query.filter_by(email=payload["email"]).first():
        raise ConflictError("Email já cadastrado")
    user = User(name=payload["name"], email=payload["email"], role=payload["role"])
    user.set_password(payload["password"])
    db.session.add(user)
    db.session.commit()
    return public_dict(user)


def update_user(user_id: int, payload: dict) -> dict:
    user = db.session.get(User, user_id)
    if not user:
        raise NotFoundError("Usuário não encontrado")

    if "email" in payload:
        clash = User.query.filter_by(email=payload["email"]).first()
        if clash and clash.id != user_id:
            raise ConflictError("Email já cadastrado")
        user.email = payload["email"]
    if "name" in payload:
        user.name = payload["name"]
    if "password" in payload:
        user.set_password(payload["password"])
    if "role" in payload:
        user.role = payload["role"]
    if "active" in payload:
        user.active = payload["active"]
    db.session.commit()
    return public_dict(user)


def delete_user(user_id: int) -> None:
    """Delete user + their tasks atomically."""
    user = db.session.get(User, user_id)
    if not user:
        raise NotFoundError("Usuário não encontrado")
    try:
        Task.query.filter_by(user_id=user_id).delete(synchronize_session=False)
        db.session.delete(user)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise


def authenticate(email: str, password: str) -> User:
    if not email or not password:
        raise ValidationError("Email e senha são obrigatórios")
    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        raise AuthError("Credenciais inválidas")
    if not user.active:
        raise AuthError("Usuário inativo", status=403)
    return user
