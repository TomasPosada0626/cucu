from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _clear_rate_limit_hits():
    from app.rate_limit import _hits

    _hits.clear()
    yield
    _hits.clear()


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setattr("app.factory.DATABASE_PATH", str(tmp_path / "auth.db"))

    from app.factory import create_app

    flask_app = create_app()
    flask_app.config["TESTING"] = True
    yield flask_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_service(app):
    return app.config["auth_service"]
