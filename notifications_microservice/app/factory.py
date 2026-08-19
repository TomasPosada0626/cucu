from __future__ import annotations

import os

from flask import Flask

from .api.errors import register_error_handlers
from .logging_utils import configure_structured_logging
from .api.routes import notifications_bp
from .repositories.notification_repository import PostgresNotificationRepository
from .services import NotificationService


def postgres_dsn() -> str:
    return os.getenv(
        "NOTIFICATIONS_POSTGRES_DSN",
        "postgresql://{user}:{password}@{host}:{port}/{db}".format(
            user=os.getenv("POSTGRES_USER", "cucu"),
            password=os.getenv("POSTGRES_PASSWORD", ""),
            host=os.getenv("POSTGRES_HOST", "postgres"),
            port=os.getenv("POSTGRES_PORT", "5432"),
            db=os.getenv("POSTGRES_DB", "cucu"),
        ),
    )


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["JSON_SORT_KEYS"] = False
    configure_structured_logging(app)

    schema = os.getenv("NOTIFICATIONS_POSTGRES_SCHEMA", "notifications_service")
    repository = PostgresNotificationRepository(postgres_dsn(), schema=schema)
    repository.initialize()

    app.config["notification_service"] = NotificationService(repository=repository)

    app.register_blueprint(notifications_bp)
    register_error_handlers(app)

    return app
