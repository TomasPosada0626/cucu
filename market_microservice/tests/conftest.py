from __future__ import annotations

import pytest


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("MARKET_DATABASE_PATH", str(tmp_path / "market.db"))

    from app.factory import create_app

    flask_app = create_app()
    flask_app.config["TESTING"] = True
    yield flask_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def market_service(app):
    return app.config["market_service"]
