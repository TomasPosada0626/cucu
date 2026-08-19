from __future__ import annotations

import os

import psycopg
import pytest

TEST_SCHEMA = "support_service_test"


def _test_dsn() -> str:
    return "postgresql://{user}:{password}@{host}:{port}/{db}".format(
        user=os.getenv("POSTGRES_USER", "cucu"),
        password=os.getenv("POSTGRES_PASSWORD", ""),
        host=os.getenv("POSTGRES_HOST", "postgres"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        db=os.getenv("POSTGRES_DB", "cucu"),
    )


def _truncate():
    with psycopg.connect(_test_dsn()) as connection:
        connection.execute(f'TRUNCATE TABLE "{TEST_SCHEMA}".ratings RESTART IDENTITY')
        connection.execute(f'TRUNCATE TABLE "{TEST_SCHEMA}".certificates RESTART IDENTITY')
        connection.execute(f'TRUNCATE TABLE "{TEST_SCHEMA}".transactions RESTART IDENTITY')
        connection.commit()


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv("SUPPORT_POSTGRES_SCHEMA", TEST_SCHEMA)

    from app.factory import create_app

    flask_app = create_app()
    flask_app.config["TESTING"] = True

    _truncate()

    yield flask_app


@pytest.fixture
def client(app):
    return app.test_client()
