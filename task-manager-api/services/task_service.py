"""Task domain service.

Lives between routes and models — encapsulates the rules that were
previously duplicated inline across 5 handlers (overdue calculation,
joined listings, stats aggregation).
"""
from datetime import datetime, timezone

from sqlalchemy.orm import joinedload

from database import db
from middlewares.error_handler import NotFoundError
from models.category import Category
from models.task import Task
from models.user import User
from schemas.constants import VALID_STATUSES
from services.notification_service import notification_service


def _enrich(task: Task, *, include_relations: bool = True) -> dict:
    data = task.to_dict()
    data["overdue"] = task.is_overdue()
    if include_relations:
        data["user_name"] = task.user.name if task.user else None
        data["category_name"] = task.category.name if task.category else None
    return data


def list_tasks(*, page: int = 1, per_page: int = 20) -> list[dict]:
    """Return enriched tasks with user/category eager-loaded (no N+1)."""
    query = Task.query.options(
        joinedload(Task.user), joinedload(Task.category)
    ).order_by(Task.id)
    tasks = query.limit(per_page).offset((page - 1) * per_page).all()
    return [_enrich(t) for t in tasks]


def get_task(task_id: int) -> dict:
    task = db.session.get(Task, task_id)
    if not task:
        raise NotFoundError("Task não encontrada")
    return _enrich(task)


def create_task(payload: dict) -> dict:
    # FK existence checks — raise domain errors so the error handler
    # converts them to proper HTTP codes.
    if payload.get("user_id"):
        if not db.session.get(User, payload["user_id"]):
            raise NotFoundError("Usuário não encontrado")
    if payload.get("category_id"):
        if not db.session.get(Category, payload["category_id"]):
            raise NotFoundError("Categoria não encontrada")

    task = Task(
        title=payload["title"],
        description=payload.get("description", ""),
        status=payload.get("status", "pending"),
        priority=payload.get("priority", 3),
        user_id=payload.get("user_id"),
        category_id=payload.get("category_id"),
        due_date=payload.get("due_date"),
        tags=payload.get("tags"),
    )
    db.session.add(task)
    db.session.commit()

    # Connect the previously orphan NotificationService — assignment fires
    # only when there is a user attached.
    if task.user_id:
        user = db.session.get(User, task.user_id)
        if user:
            notification_service.notify_task_assigned(user, task)

    return _enrich(task)


def update_task(task_id: int, payload: dict) -> dict:
    task = db.session.get(Task, task_id)
    if not task:
        raise NotFoundError("Task não encontrada")

    if "user_id" in payload and payload["user_id"]:
        if not db.session.get(User, payload["user_id"]):
            raise NotFoundError("Usuário não encontrado")
    if "category_id" in payload and payload["category_id"]:
        if not db.session.get(Category, payload["category_id"]):
            raise NotFoundError("Categoria não encontrada")

    for field, value in payload.items():
        setattr(task, field, value)
    task.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    return _enrich(task)


def delete_task(task_id: int) -> None:
    task = db.session.get(Task, task_id)
    if not task:
        raise NotFoundError("Task não encontrada")
    db.session.delete(task)
    db.session.commit()


def search_tasks(*, q: str = "", status: str = "", priority: str = "", user_id: str = "") -> list[dict]:
    query = Task.query.options(joinedload(Task.user), joinedload(Task.category))
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(Task.title.like(like), Task.description.like(like)))
    if status:
        query = query.filter(Task.status == status)
    if priority:
        try:
            query = query.filter(Task.priority == int(priority))
        except ValueError:
            pass
    if user_id:
        try:
            query = query.filter(Task.user_id == int(user_id))
        except ValueError:
            pass
    return [t.to_dict() for t in query.all()]


def get_stats() -> dict:
    """Aggregate task stats — single trip per metric (no Python loop)."""
    base = Task.query
    total = base.count()
    counts = {s: base.filter(Task.status == s).count() for s in VALID_STATUSES}
    done = counts.get("done", 0)

    overdue = sum(
        1
        for t in Task.query.with_entities(Task.due_date, Task.status).all()
        if t.due_date and t.due_date < datetime.utcnow() and t.status not in ("done", "cancelled")
    )

    return {
        "total": total,
        "pending": counts.get("pending", 0),
        "in_progress": counts.get("in_progress", 0),
        "done": done,
        "cancelled": counts.get("cancelled", 0),
        "overdue": overdue,
        "completion_rate": round((done / total) * 100, 2) if total > 0 else 0,
    }


def list_for_user(user_id: int) -> list[dict]:
    user = db.session.get(User, user_id)
    if not user:
        raise NotFoundError("Usuário não encontrado")
    tasks = Task.query.filter_by(user_id=user_id).all()
    return [_enrich(t, include_relations=False) for t in tasks]


def notify_overdue() -> int:
    """Fire overdue notifications via NotificationService. Returns count."""
    count = 0
    overdue_tasks = (
        Task.query.options(joinedload(Task.user))
        .filter(Task.due_date.isnot(None))
        .all()
    )
    for task in overdue_tasks:
        if task.is_overdue() and task.user:
            notification_service.notify_task_overdue(task.user, task)
            count += 1
    return count
