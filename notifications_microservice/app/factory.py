from __future__ import annotations

import os
from pathlib import Path

from flask import Flask

from .api.errors import register_error_handlers
from .logging_utils import configure_structured_logging
from .api.routes import notifications_bp
from .repositories.notification_repository import SQLiteNotificationRepository
from .services import NotificationService


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["JSON_SORT_KEYS"] = False
    configure_structured_logging(app)

    database_path = os.getenv("NOTIFICATIONS_DATABASE_PATH", str(Path(app.root_path).parent / "data" / "notifications.db"))

    repository = SQLiteNotificationRepository(database_path)
    repository.initialize()

    app.config["notification_service"] = NotificationService(repository=repository)

    app.register_blueprint(notifications_bp)
    register_error_handlers(app)

    return app
