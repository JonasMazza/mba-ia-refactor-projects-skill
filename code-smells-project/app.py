"""Entry point / composition root.

Boots Flask, loads config, configures logging, initializes the DB schema,
registers CORS, blueprints, error handlers, and the request-scoped DB
teardown. Holds no business logic.
"""
from flask import Flask
from flask_cors import CORS

from src.config.logging_config import configure_logging
from src.config.settings import settings
from src.database import close_db, init_db
from src.middlewares.errors import register_error_handlers
from src.routes.admin_routes import admin_bp
from src.routes.pedido_routes import pedido_bp
from src.routes.produto_routes import produto_bp
from src.routes.report_routes import report_bp
from src.routes.system_routes import system_bp
from src.routes.usuario_routes import usuario_bp


def create_app() -> Flask:
    configure_logging(settings.LOG_LEVEL)

    app = Flask(__name__)
    app.config["SECRET_KEY"] = settings.SECRET_KEY
    app.config["DEBUG"] = settings.DEBUG

    # CORS allowlist (PB16 / AP16). "*" allowed only via env override.
    origins = (
        "*"
        if settings.CORS_ORIGINS.strip() == "*"
        else [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
    )
    CORS(app, origins=origins)

    init_db()
    app.teardown_appcontext(close_db)

    app.register_blueprint(system_bp)
    app.register_blueprint(produto_bp)
    app.register_blueprint(usuario_bp)
    app.register_blueprint(pedido_bp)
    app.register_blueprint(report_bp)
    app.register_blueprint(admin_bp)

    register_error_handlers(app)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=settings.PORT, debug=settings.DEBUG)
