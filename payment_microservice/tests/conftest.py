from __future__ import annotations

import os
from unittest import mock

import psycopg
import pytest

TEST_SCHEMA = "payment_service_test"


def _test_dsn() -> str:
    return "postgresql://{user}:{password}@{host}:{port}/{db}".format(
        user=os.getenv("POSTGRES_USER", "cucu"),
        password=os.getenv("POSTGRES_PASSWORD", ""),
        host=os.getenv("POSTGRES_HOST", "postgres"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        db=os.getenv("POSTGRES_DB", "cucu"),
    )


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv("PAYMENTS_POSTGRES_SCHEMA", TEST_SCHEMA)
    # Evita que create_app() intente publicar eventos a un RabbitMQ real
    # cuando los tests de rutas ejercitan el flujo completo de create_payment.
    monkeypatch.setattr(
        "app.events.RabbitMQPaymentEventPublisher.publish_payment_processed",
        mock.MagicMock(),
    )

    from app.factory import create_app

    flask_app = create_app()
    flask_app.config["TESTING"] = True

    with psycopg.connect(_test_dsn()) as connection:
        connection.execute(f'TRUNCATE TABLE "{TEST_SCHEMA}".payments')
        connection.commit()

    yield flask_app


@pytest.fixture
def client(app):
    return app.test_client()
