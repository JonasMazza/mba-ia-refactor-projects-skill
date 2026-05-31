"""User HTTP routes — thin handlers that delegate to services."""
from flask import Blueprint, jsonify, request

from middlewares.auth import encode_token, requires_auth
from schemas.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from schemas.user_schema import parse_create, parse_update
from services import task_service, user_service

user_bp = Blueprint("users", __name__)


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


@user_bp.route("/users", methods=["GET"])
@requires_auth(role="admin")
def get_users():
    page, per_page = _pagination_args()
    return jsonify(user_service.list_users(page=page, per_page=per_page)), 200


@user_bp.route("/users/<int:user_id>", methods=["GET"])
@requires_auth()
def get_user(user_id):
    return jsonify(user_service.get_user(user_id)), 200


@user_bp.route("/users", methods=["POST"])
def create_user():
    payload = parse_create(request.get_json(silent=True) or {})
    return jsonify(user_service.create_user(payload)), 201


@user_bp.route("/users/<int:user_id>", methods=["PUT"])
@requires_auth()
def update_user(user_id):
    payload = parse_update(request.get_json(silent=True) or {})
    return jsonify(user_service.update_user(user_id, payload)), 200


@user_bp.route("/users/<int:user_id>", methods=["DELETE"])
@requires_auth(role="admin")
def delete_user(user_id):
    user_service.delete_user(user_id)
    return jsonify({"message": "Usuário deletado com sucesso"}), 200


@user_bp.route("/users/<int:user_id>/tasks", methods=["GET"])
def get_user_tasks(user_id):
    return jsonify(task_service.list_for_user(user_id)), 200


@user_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    user = user_service.authenticate(data.get("email"), data.get("password"))
    return jsonify({
        "message": "Login realizado com sucesso",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "active": user.active,
        },
        "token": encode_token(user),
    }), 200
