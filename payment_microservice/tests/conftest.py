from __future__ import annotations

from unittest import mock

import pytest


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("PAYMENTS_DATABASE_PATH", str(tmp_path / "payments.db"))
    # Evita que create_app() intente publicar eventos a un RabbitMQ real
    # cuando los tests de rutas ejercitan el flujo completo de create_payment.
    monkeypatch.setattr(
        "app.events.RabbitMQPaymentEventPublisher.publish_payment_processed",
        mock.MagicMock(),
    )

    from app.factory import create_app

    flask_app = create_app()
    flask_app.config["TESTING"] = True
    yield flask_app


@pytest.fixture
def client(app):
    return app.test_client()
