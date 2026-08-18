from __future__ import annotations

from flask import Flask

from .api.errors import register_error_handlers
from .api.routes import auth_bp
from .logging_utils import configure_structured_logging
from .repositories.auth_repository import PostgresAuthRepository
from .services import AuthService
from .settings import POSTGRES_DSN, POSTGRES_SCHEMA


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["JSON_SORT_KEYS"] = False
    configure_structured_logging(app)

    repository = PostgresAuthRepository(POSTGRES_DSN, schema=POSTGRES_SCHEMA)
    repository.initialize()

    app.config["auth_service"] = AuthService(repository=repository)

    app.register_blueprint(auth_bp)
    register_error_handlers(app)

    return app
