from __future__ import annotations

from flask import Flask

from .api.errors import register_error_handlers
from .api.routes import auth_bp
from .repositories.auth_repository import SQLiteAuthRepository
from .services import AuthService
from .settings import DATABASE_PATH


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["JSON_SORT_KEYS"] = False

    repository = SQLiteAuthRepository(DATABASE_PATH)
    repository.initialize()

    app.config["auth_service"] = AuthService(repository=repository)

    app.register_blueprint(auth_bp)
    register_error_handlers(app)

    return app
