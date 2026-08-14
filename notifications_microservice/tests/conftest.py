from __future__ import annotations

import pytest


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("NOTIFICATIONS_DATABASE_PATH", str(tmp_path / "notifications.db"))

    from app.factory import create_app

    flask_app = create_app()
    flask_app.config["TESTING"] = True
    yield flask_app


@pytest.fixture
def client(app):
    return app.test_client()
