from __future__ import annotations


def _create(client, usuario_id=1, tipo="pedido", mensaje="Hola"):
    return client.post(
        "/api/v3/notifications", json={"usuario_id": usuario_id, "tipo": tipo, "mensaje": mensaje}
    )


def test_health_check(client):
    assert client.get("/health").status_code == 200


def test_create_notification_success(client):
    response = _create(client)
    assert response.status_code == 201
    assert response.get_json()["data"]["mensaje"] == "Hola"


def test_create_notification_non_json_returns_400(client):
    response = client.post("/api/v3/notifications", data="not json", content_type="text/plain")
    assert response.status_code == 400


def test_create_notification_invalid_tipo_returns_400(client):
    response = _create(client, tipo="no-valido")
    assert response.status_code == 400


def test_get_user_notifications_requires_usuario_id(client):
    response = client.get("/api/v3/notifications")
    assert response.status_code == 400


def test_get_user_notifications_returns_only_own(client):
    _create(client, usuario_id=1, mensaje="Mia")
    _create(client, usuario_id=2, mensaje="Ajena")

    response = client.get("/api/v3/notifications", query_string={"usuario_id": 1})

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert len(data) == 1
    assert data[0]["mensaje"] == "Mia"


def test_mark_notification_as_read_success(client):
    notif_id = _create(client).get_json()["data"]["id"]
    response = client.post(f"/api/v3/notifications/{notif_id}/read")
    assert response.status_code == 200
    assert response.get_json()["data"]["leida"] is True


def test_mark_notification_as_read_not_found_returns_404(client):
    response = client.post("/api/v3/notifications/999999/read")
    assert response.status_code == 404


def test_mark_notification_as_read_already_read_returns_409(client):
    notif_id = _create(client).get_json()["data"]["id"]
    client.post(f"/api/v3/notifications/{notif_id}/read")
    response = client.post(f"/api/v3/notifications/{notif_id}/read")
    assert response.status_code == 409


def test_api_error_with_details_included_in_response(client, app, monkeypatch):
    from app.errors import ValidationError

    def _boom(**kwargs):
        raise ValidationError("invalido", details={"field": "tipo"})

    monkeypatch.setattr(app.config["notification_service"], "create_notification", _boom)

    response = _create(client)

    assert response.status_code == 400
    assert response.get_json()["error"]["details"] == {"field": "tipo"}


def test_unexpected_error_returns_500(client, app, monkeypatch):
    app.config["TESTING"] = False
    app.config["PROPAGATE_EXCEPTIONS"] = False

    def _boom(**kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(app.config["notification_service"], "create_notification", _boom)

    response = _create(client)

    assert response.status_code == 500
    assert response.get_json()["error"]["code"] == "internal_server_error"
