from __future__ import annotations

import os

from flask import Flask

from .api.errors import register_error_handlers
from .logging_utils import configure_structured_logging
from .api.routes import support_bp
from .repositories.support_repository import PostgresSupportRepository
from .services import SupportService


def _postgres_dsn() -> str:
    return os.getenv(
        "SUPPORT_POSTGRES_DSN",
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

    schema = os.getenv("SUPPORT_POSTGRES_SCHEMA", "support_service")
    repository = PostgresSupportRepository(_postgres_dsn(), schema=schema)
    repository.initialize()

    app.config["support_service"] = SupportService(repository=repository)

    app.register_blueprint(support_bp)
    register_error_handlers(app)

    return app
