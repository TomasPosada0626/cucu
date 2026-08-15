from __future__ import annotations

import os
from pathlib import Path

from flask import Flask

from .api.errors import register_error_handlers
from .logging_utils import configure_structured_logging
from .api.routes import support_bp
from .repositories.support_repository import SQLiteSupportRepository
from .services import SupportService


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["JSON_SORT_KEYS"] = False
    configure_structured_logging(app)

    database_path = os.getenv("SUPPORT_DATABASE_PATH", str(Path(app.root_path).parent / "data" / "support.db"))

    repository = SQLiteSupportRepository(database_path)
    repository.initialize()

    app.config["support_service"] = SupportService(repository=repository)

    app.register_blueprint(support_bp)
    register_error_handlers(app)

    return app
