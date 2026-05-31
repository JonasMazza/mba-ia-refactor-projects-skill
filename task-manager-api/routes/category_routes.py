"""Category HTTP routes — extracted from report_routes.py.

Same URLs as before (`/categories`), so the public API is preserved.
"""
from flask import Blueprint, jsonify, request

from middlewares.auth import requires_auth
from schemas.category_schema import parse_create, parse_update
from services import category_service, report_service

category_bp = Blueprint("categories", __name__)


@category_bp.route("/categories", methods=["GET"])
def get_categories():
    return jsonify(report_service.list_categories_with_counts()), 200


@category_bp.route("/categories", methods=["POST"])
@requires_auth()
def create_category():
    payload = parse_create(request.get_json(silent=True) or {})
    return jsonify(category_service.create_category(payload)), 201


@category_bp.route("/categories/<int:cat_id>", methods=["PUT"])
@requires_auth()
def update_category(cat_id):
    payload = parse_update(request.get_json(silent=True) or {})
    return jsonify(category_service.update_category(cat_id, payload)), 200


@category_bp.route("/categories/<int:cat_id>", methods=["DELETE"])
@requires_auth(role="admin")
def delete_category(cat_id):
    category_service.delete_category(cat_id)
    return jsonify({"message": "Categoria deletada"}), 200
