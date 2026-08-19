from __future__ import annotations

import os

import psycopg
import pytest

TEST_SCHEMA = "notifications_service_test"


def _test_dsn() -> str:
    return "postgresql://{user}:{password}@{host}:{port}/{db}".format(
        user=os.getenv("POSTGRES_USER", "cucu"),
        password=os.getenv("POSTGRES_PASSWORD", ""),
        host=os.getenv("POSTGRES_HOST", "postgres"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        db=os.getenv("POSTGRES_DB", "cucu"),
    )


def _truncate():
    # Se llama tambien desde fixtures que no pasan por create_app() (worker),
    # asi que se asegura el schema/tablas antes de intentar vaciarlas.
    from app.repositories.notification_repository import PostgresNotificationRepository

    PostgresNotificationRepository(_test_dsn(), schema=TEST_SCHEMA).initialize()

    with psycopg.connect(_test_dsn()) as connection:
        connection.execute(f'TRUNCATE TABLE "{TEST_SCHEMA}".notifications RESTART IDENTITY')
        connection.execute(f'TRUNCATE TABLE "{TEST_SCHEMA}".processed_events')
        connection.commit()


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv("NOTIFICATIONS_POSTGRES_SCHEMA", TEST_SCHEMA)

    from app.factory import create_app

    flask_app = create_app()
    flask_app.config["TESTING"] = True

    _truncate()

    yield flask_app


@pytest.fixture
def client(app):
    return app.test_client()
