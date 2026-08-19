from __future__ import annotations

import os

from flask import Flask

from .api.errors import register_error_handlers
from .logging_utils import configure_structured_logging
from .api.routes import payments_bp
from .events import RabbitMQPaymentEventPublisher
from .repositories.payment_repository import PostgresPaymentRepository
from .services.payment_service import PaymentService


def _postgres_dsn() -> str:
    return os.getenv(
        "PAYMENTS_POSTGRES_DSN",
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

    schema = os.getenv("PAYMENTS_POSTGRES_SCHEMA", "payment_service")
    repository = PostgresPaymentRepository(_postgres_dsn(), schema=schema)
    repository.initialize()

    event_publisher = RabbitMQPaymentEventPublisher()
    app.config["payment_service"] = PaymentService(repository=repository, event_publisher=event_publisher)

    app.register_blueprint(payments_bp)
    register_error_handlers(app)

    return app
