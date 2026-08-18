from __future__ import annotations

import os

import psycopg
import pytest

TEST_SCHEMA = "auth_service_test"


def _test_dsn() -> str:
    return "postgresql://{user}:{password}@{host}:{port}/{db}".format(
        user=os.getenv("POSTGRES_USER", "cucu"),
        password=os.getenv("POSTGRES_PASSWORD", ""),
        host=os.getenv("POSTGRES_HOST", "postgres"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        db=os.getenv("POSTGRES_DB", "cucu"),
    )


@pytest.fixture(autouse=True)
def _clear_rate_limit_hits():
    from app.rate_limit import _hits

    _hits.clear()
    yield
    _hits.clear()


@pytest.fixture
def app(monkeypatch):
    dsn = _test_dsn()
    monkeypatch.setattr("app.factory.POSTGRES_DSN", dsn)
    monkeypatch.setattr("app.factory.POSTGRES_SCHEMA", TEST_SCHEMA)

    from app.factory import create_app

    flask_app = create_app()
    flask_app.config["TESTING"] = True

    with psycopg.connect(dsn) as connection:
        connection.execute(f'TRUNCATE TABLE "{TEST_SCHEMA}".users RESTART IDENTITY')
        connection.commit()

    yield flask_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_service(app):
    return app.config["auth_service"]
