"""Task HTTP routes — thin handlers that delegate to services."""
from flask import Blueprint, jsonify, request

from middlewares.auth import requires_auth
from schemas.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from schemas.task_schema import parse_create, parse_update
from services import task_service

task_bp = Blueprint("tasks", __name__)


def _pagination_args() -> tuple[int, int]:
    try:
        page = max(int(request.args.get("page", 1)), 1)
    except ValueError:
        page = 1
    try:
        per_page = int(request.args.get("per_page", DEFAULT_PAGE_SIZE))
    except ValueError:
        per_page = DEFAULT_PAGE_SIZE
    per_page = max(1, min(per_page, MAX_PAGE_SIZE))
    return page, per_page


@task_bp.route("/tasks", methods=["GET"])
def get_tasks():
    page, per_page = _pagination_args()
    return jsonify(task_service.list_tasks(page=page, per_page=per_page)), 200


@task_bp.route("/tasks/<int:task_id>", methods=["GET"])
def get_task(task_id):
    return jsonify(task_service.get_task(task_id)), 200


@task_bp.route("/tasks", methods=["POST"])
@requires_auth()
def create_task():
    payload = parse_create(request.get_json(silent=True) or {})
    return jsonify(task_service.create_task(payload)), 201


@task_bp.route("/tasks/<int:task_id>", methods=["PUT"])
@requires_auth()
def update_task(task_id):
    payload = parse_update(request.get_json(silent=True) or {})
    return jsonify(task_service.update_task(task_id, payload)), 200


@task_bp.route("/tasks/<int:task_id>", methods=["DELETE"])
@requires_auth()
def delete_task(task_id):
    task_service.delete_task(task_id)
    return jsonify({"message": "Task deletada com sucesso"}), 200


@task_bp.route("/tasks/search", methods=["GET"])
def search_tasks():
    return jsonify(task_service.search_tasks(
        q=request.args.get("q", ""),
        status=request.args.get("status", ""),
        priority=request.args.get("priority", ""),
        user_id=request.args.get("user_id", ""),
    )), 200


@task_bp.route("/tasks/stats", methods=["GET"])
def task_stats():
    return jsonify(task_service.get_stats()), 200
