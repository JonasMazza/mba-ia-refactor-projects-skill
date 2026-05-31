"""Reports: aggregate stats for the whole system or per-user."""
from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import joinedload

from database import db
from middlewares.error_handler import NotFoundError
from models.category import Category
from models.task import Task
from models.user import User


def _utc_now_naive():
    # SQLite stores naive datetimes; compare same-shape to avoid issues.
    return datetime.utcnow()


def build_summary() -> dict:
    total_tasks = Task.query.count()
    total_users = User.query.count()
    total_categories = Category.query.count()

    # Single GROUP BY query for status counts (was 4 separate counts).
    status_rows = (
        db.session.query(Task.status, func.count(Task.id))
        .group_by(Task.status)
        .all()
    )
    by_status = {s: 0 for s in ("pending", "in_progress", "done", "cancelled")}
    for status, cnt in status_rows:
        if status in by_status:
            by_status[status] = cnt

    priority_rows = (
        db.session.query(Task.priority, func.count(Task.id))
        .group_by(Task.priority)
        .all()
    )
    by_priority_raw = {p: 0 for p in (1, 2, 3, 4, 5)}
    for p, cnt in priority_rows:
        if p in by_priority_raw:
            by_priority_raw[p] = cnt

    # Overdue list: one query then filter in Python (cleaner than CASE).
    overdue_list = []
    now = _utc_now_naive()
    candidate_tasks = (
        Task.query.filter(Task.due_date.isnot(None))
        .filter(Task.status.notin_(("done", "cancelled")))
        .all()
    )
    for t in candidate_tasks:
        if t.due_date < now:
            overdue_list.append({
                "id": t.id,
                "title": t.title,
                "due_date": str(t.due_date),
                "days_overdue": (now - t.due_date).days,
            })

    seven_days_ago = now - timedelta(days=7)
    recent_tasks = Task.query.filter(Task.created_at >= seven_days_ago).count()
    recent_done = Task.query.filter(
        Task.status == "done", Task.updated_at >= seven_days_ago
    ).count()

    # User productivity — one users query + one grouped tasks query.
    users = User.query.all()
    task_counts = dict(
        db.session.query(Task.user_id, func.count(Task.id))
        .group_by(Task.user_id)
        .all()
    )
    done_counts = dict(
        db.session.query(Task.user_id, func.count(Task.id))
        .filter(Task.status == "done")
        .group_by(Task.user_id)
        .all()
    )
    user_stats = []
    for u in users:
        total = task_counts.get(u.id, 0)
        completed = done_counts.get(u.id, 0)
        user_stats.append({
            "user_id": u.id,
            "user_name": u.name,
            "total_tasks": total,
            "completed_tasks": completed,
            "completion_rate": round((completed / total) * 100, 2) if total > 0 else 0,
        })

    return {
        "generated_at": str(datetime.now(timezone.utc)),
        "overview": {
            "total_tasks": total_tasks,
            "total_users": total_users,
            "total_categories": total_categories,
        },
        "tasks_by_status": by_status,
        "tasks_by_priority": {
            "critical": by_priority_raw[1],
            "high": by_priority_raw[2],
            "medium": by_priority_raw[3],
            "low": by_priority_raw[4],
            "minimal": by_priority_raw[5],
        },
        "overdue": {
            "count": len(overdue_list),
            "tasks": overdue_list,
        },
        "recent_activity": {
            "tasks_created_last_7_days": recent_tasks,
            "tasks_completed_last_7_days": recent_done,
        },
        "user_productivity": user_stats,
    }


def build_user_report(user_id: int) -> dict:
    user = db.session.get(User, user_id)
    if not user:
        raise NotFoundError("Usuário não encontrado")

    tasks = Task.query.filter_by(user_id=user_id).all()
    total = len(tasks)
    counters = {"done": 0, "pending": 0, "in_progress": 0, "cancelled": 0}
    overdue = 0
    high_priority = 0
    now = _utc_now_naive()

    for t in tasks:
        if t.status in counters:
            counters[t.status] += 1
        if t.priority is not None and t.priority <= 2:
            high_priority += 1
        if t.due_date and t.due_date < now and t.status not in ("done", "cancelled"):
            overdue += 1

    done = counters["done"]
    return {
        "user": {"id": user.id, "name": user.name, "email": user.email},
        "statistics": {
            "total_tasks": total,
            "done": done,
            "pending": counters["pending"],
            "in_progress": counters["in_progress"],
            "cancelled": counters["cancelled"],
            "overdue": overdue,
            "high_priority": high_priority,
            "completion_rate": round((done / total) * 100, 2) if total > 0 else 0,
        },
    }


def list_categories_with_counts() -> list[dict]:
    """Categories + task_count using a LEFT JOIN (no N+1)."""
    rows = (
        db.session.query(Category, func.count(Task.id))
        .outerjoin(Task, Task.category_id == Category.id)
        .group_by(Category.id)
        .all()
    )
    result = []
    for category, count in rows:
        data = category.to_dict()
        data["task_count"] = count
        result.append(data)
    return result
