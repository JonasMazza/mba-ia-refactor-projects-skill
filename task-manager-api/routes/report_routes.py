"""Report HTTP routes — thin handlers over report_service."""
from flask import Blueprint, jsonify

from services import report_service

report_bp = Blueprint("reports", __name__)


@report_bp.route("/reports/summary", methods=["GET"])
def summary_report():
    return jsonify(report_service.build_summary()), 200


@report_bp.route("/reports/user/<int:user_id>", methods=["GET"])
def user_report(user_id):
    return jsonify(report_service.build_user_report(user_id)), 200
