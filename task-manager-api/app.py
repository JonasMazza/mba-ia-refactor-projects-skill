"""Composition root.

Builds the Flask app, wires config, middlewares, blueprints, and CLI commands.
Schema creation is exposed as `flask --app app.py init-db` (or
`python -m app init-db`) — NOT executed at import time.
"""
from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone

from flask import Flask, jsonify
from flask_cors import CORS

from config.settings import settings
from database import db
from middlewares.error_handler import register_error_handlers
from routes.category_routes import category_bp
from routes.report_routes import report_bp
from routes.task_routes import task_bp
from routes.user_routes import user_bp


def create_app() -> Flask:
    app = Flask(__name__)

    app.config["SQLALCHEMY_DATABASE_URI"] = settings.DB_URL
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = settings.SECRET_KEY
    app.config["DEBUG"] = settings.DEBUG

    logging.basicConfig(
        level=logging.DEBUG if settings.DEBUG else logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )

    CORS(app, origins=settings.CORS_ORIGINS)
    db.init_app(app)

    # Blueprints
    app.register_blueprint(task_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(report_bp)
    app.register_blueprint(category_bp)

    register_error_handlers(app)

    @app.route("/health")
    def health():
        return jsonify({"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()})

    @app.route("/")
    def index():
        return jsonify({"message": "Task Manager API", "version": "2.0"})

    # CLI commands
    @app.cli.command("init-db")
    def init_db_command():
        """Create database schema."""
        with app.app_context():
            db.create_all()
        print("Database initialized.")

    @app.cli.command("seed")
    def seed_command():
        """Populate the database with dev data."""
        from seed import seed_data
        seed_data(app)

    return app


app = create_app()


def _run_cli_command(argv: list[str]) -> int:
    """Tiny CLI dispatcher so users can run `python -m app init-db`."""
    if not argv:
        return -1
    cmd = argv[0]
    if cmd == "init-db":
        with app.app_context():
            db.create_all()
        print("Database initialized.")
        return 0
    if cmd == "seed":
        from seed import seed_data
        seed_data(app)
        return 0
    print(f"Unknown command: {cmd}. Available: init-db, seed", file=sys.stderr)
    return 2


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ("init-db", "seed"):
        sys.exit(_run_cli_command(sys.argv[1:]))
    app.run(debug=settings.DEBUG, host="0.0.0.0", port=settings.PORT)
