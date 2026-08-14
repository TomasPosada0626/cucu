from __future__ import annotations

import sqlite3



def _register(client, *, username="testuser", email="test@example.com", password="secret123"):
    return client.post(
        "/api/v3/auth/register",
        json={"username": username, "email": email, "password": password},
    )


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_register_success(client):
    response = _register(client)
    assert response.status_code == 201
    body = response.get_json()["data"]
    assert body["user"]["username"] == "testuser"
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["token_type"] == "Bearer"


def test_register_non_json_body_returns_400(client):
    response = client.post("/api/v3/auth/register", data="not json", content_type="text/plain")
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "validation_error"


def test_register_short_username_returns_400(client):
    response = _register(client, username="ab")
    assert response.status_code == 400


def test_register_invalid_email_returns_400(client):
    response = _register(client, email="not-an-email")
    assert response.status_code == 400


def test_register_short_password_returns_400(client):
    response = _register(client, password="123")
    assert response.status_code == 400


def test_register_duplicate_username_returns_409(client):
    _register(client, username="dup", email="dup1@example.com")
    response = _register(client, username="dup", email="dup2@example.com")
    assert response.status_code == 409


def test_register_duplicate_email_returns_409(client):
    _register(client, username="user1", email="same@example.com")
    response = _register(client, username="user2", email="same@example.com")
    assert response.status_code == 409


def test_login_success(client):
    _register(client, email="login@example.com", password="secret123")
    response = client.post(
        "/api/v3/auth/login", json={"email": "login@example.com", "password": "secret123"}
    )
    assert response.status_code == 200
    assert "access_token" in response.get_json()["data"]


def test_login_wrong_password_returns_401(client):
    _register(client, email="login2@example.com", password="secret123")
    response = client.post(
        "/api/v3/auth/login", json={"email": "login2@example.com", "password": "wrong"}
    )
    assert response.status_code == 401


def test_login_unknown_email_returns_401(client):
    response = client.post(
        "/api/v3/auth/login", json={"email": "no-existe@example.com", "password": "secret123"}
    )
    assert response.status_code == 401


def test_refresh_success(client):
    register_response = _register(client, email="refresh@example.com")
    refresh_token = register_response.get_json()["data"]["refresh_token"]

    response = client.post("/api/v3/auth/refresh", json={"refresh_token": refresh_token})

    assert response.status_code == 200
    assert "access_token" in response.get_json()["data"]


def test_refresh_missing_token_returns_401(client):
    response = client.post("/api/v3/auth/refresh", json={})
    assert response.status_code == 401


def _delete_user(app, user_id):
    db_path = app.config["auth_service"].repository.database_path
    with sqlite3.connect(db_path) as connection:
        connection.execute("DELETE FROM users WHERE id = ?", (user_id,))
        connection.commit()


def test_refresh_for_deleted_user_returns_404(client, app):
    register_response = _register(client, email="deleted_refresh@example.com")
    body = register_response.get_json()["data"]
    _delete_user(app, body["user"]["id"])

    response = client.post("/api/v3/auth/refresh", json={"refresh_token": body["refresh_token"]})

    assert response.status_code == 404


def test_me_for_deleted_user_returns_404(client, app):
    register_response = _register(client, email="deleted_me@example.com")
    body = register_response.get_json()["data"]
    _delete_user(app, body["user"]["id"])

    response = client.get("/api/v3/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})

    assert response.status_code == 404


def test_refresh_with_access_token_returns_401(client):
    register_response = _register(client, email="wrongtype@example.com")
    access_token = register_response.get_json()["data"]["access_token"]

    response = client.post("/api/v3/auth/refresh", json={"refresh_token": access_token})

    assert response.status_code == 401


def test_refresh_malformed_token_returns_401(client):
    response = client.post("/api/v3/auth/refresh", json={"refresh_token": "no-es-un-jwt"})
    assert response.status_code == 401


def test_me_success(client):
    register_response = _register(client, email="me@example.com")
    access_token = register_response.get_json()["data"]["access_token"]

    response = client.get("/api/v3/auth/me", headers={"Authorization": f"Bearer {access_token}"})

    assert response.status_code == 200
    assert response.get_json()["data"]["email"] == "me@example.com"


def test_me_missing_bearer_returns_400(client):
    response = client.get("/api/v3/auth/me")
    assert response.status_code == 400


def test_me_invalid_token_returns_401(client):
    response = client.get("/api/v3/auth/me", headers={"Authorization": "Bearer no-es-un-jwt"})
    assert response.status_code == 401


def test_password_reset_unknown_user_returns_404(client):
    response = client.post(
        "/api/v3/auth/password-reset",
        json={"email": "no-existe@example.com", "new_password": "nuevaClave123"},
    )
    assert response.status_code == 404


def test_password_reset_short_password_returns_400(client):
    _register(client, email="reset@example.com")
    response = client.post(
        "/api/v3/auth/password-reset", json={"email": "reset@example.com", "new_password": "123"}
    )
    assert response.status_code == 400


def test_password_reset_known_user_returns_not_implemented(client):
    _register(client, email="reset2@example.com")
    response = client.post(
        "/api/v3/auth/password-reset",
        json={"email": "reset2@example.com", "new_password": "nuevaClave123"},
    )
    assert response.status_code == 501
    assert response.get_json()["error"]["code"] == "not_implemented"


def test_api_error_with_details_included_in_response(client, app, monkeypatch):
    from app.errors import ValidationError

    def _boom(**kwargs):
        raise ValidationError("dato invalido", details={"field": "email"})

    monkeypatch.setattr(app.config["auth_service"], "login", _boom)

    response = client.post(
        "/api/v3/auth/login", json={"email": "x@example.com", "password": "secret123"}
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["details"] == {"field": "email"}


def test_unexpected_error_is_translated_to_500(client, app, monkeypatch):
    # Flask propaga excepciones no manejadas fuera del cliente de test cuando
    # TESTING/DEBUG estan activos, en vez de pasar por el errorhandler; se
    # desactiva puntualmente para poder observar la respuesta 500 real.
    app.config["TESTING"] = False
    app.config["PROPAGATE_EXCEPTIONS"] = False

    def _boom(**kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(app.config["auth_service"], "login", _boom)

    response = client.post(
        "/api/v3/auth/login", json={"email": "x@example.com", "password": "secret123"}
    )

    assert response.status_code == 500
    assert response.get_json()["error"]["code"] == "internal_server_error"
