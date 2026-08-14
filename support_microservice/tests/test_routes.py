from __future__ import annotations


def _create_rating(client, **overrides):
    payload = {"usuario": 1, "autor": 2, "puntuacion": 5, "comentario": "Excelente"}
    payload.update(overrides)
    return client.post("/api/v3/ratings", json=payload)


def test_health_check(client):
    assert client.get("/health").status_code == 200


def test_create_rating_success(client):
    response = _create_rating(client)
    assert response.status_code == 201
    assert response.get_json()["data"]["puntuacion"] == 5


def test_create_rating_accepts_usuario_id_alias(client):
    response = client.post(
        "/api/v3/ratings", json={"usuario_id": 1, "autor_id": 2, "puntuacion": 4, "comentario": "Bien"}
    )
    assert response.status_code == 201


def test_create_rating_missing_body_defaults_to_empty_and_fails(client):
    response = client.post("/api/v3/ratings", data="not json", content_type="text/plain")
    assert response.status_code == 400


def test_list_ratings_requires_usuario_param(client):
    response = client.get("/api/v3/ratings")
    assert response.status_code == 400


def test_list_ratings_returns_only_own(client):
    _create_rating(client, usuario=1)
    _create_rating(client, usuario=2)

    response = client.get("/api/v3/ratings", query_string={"usuario": 1})

    assert response.status_code == 200
    assert len(response.get_json()["data"]) == 1


def test_upsert_certificate_success(client):
    response = client.post(
        "/api/v3/trust/certificates",
        json={"usuario": 1, "archivo_url": "url", "fecha_emision": "2026-01-01", "estado_verificacion": True},
    )
    assert response.status_code == 200
    assert response.get_json()["data"]["estado_verificacion"] is True


def test_get_certificate_requires_usuario_param(client):
    response = client.get("/api/v3/trust/certificates")
    assert response.status_code == 400


def test_get_certificate_not_found_returns_404(client):
    response = client.get("/api/v3/trust/certificates", query_string={"usuario": 999})
    assert response.status_code == 404


def test_get_certificate_success(client):
    client.post(
        "/api/v3/trust/certificates",
        json={"usuario": 1, "archivo_url": "url", "fecha_emision": "2026-01-01", "estado_verificacion": False},
    )
    response = client.get("/api/v3/trust/certificates", query_string={"usuario": 1})
    assert response.status_code == 200


def test_upsert_transaction_success(client):
    response = client.post(
        "/api/v3/transactions",
        json={"pedido": 1, "estado": "ABIERTA", "distancia_validacion_metros": 0},
    )
    assert response.status_code == 200
    assert response.get_json()["data"]["estado"] == "ABIERTA"


def test_get_transaction_requires_pedido_param(client):
    response = client.get("/api/v3/transactions")
    assert response.status_code == 400


def test_get_transaction_not_found_returns_404(client):
    response = client.get("/api/v3/transactions", query_string={"pedido": 999})
    assert response.status_code == 404


def test_get_transaction_success(client):
    client.post("/api/v3/transactions", json={"pedido": 1, "estado": "ABIERTA", "distancia_validacion_metros": 0})
    response = client.get("/api/v3/transactions", query_string={"pedido": 1})
    assert response.status_code == 200


def test_unknown_route_returns_404_via_http_exception_handler(client):
    response = client.get("/api/v3/does-not-exist")
    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "not_found"


def test_api_error_with_details_included_in_response(client, app, monkeypatch):
    from app.errors import ValidationError

    def _boom(**kwargs):
        raise ValidationError("invalido", details={"field": "puntuacion"})

    monkeypatch.setattr(app.config["support_service"], "create_rating", _boom)

    response = _create_rating(client)

    assert response.status_code == 400
    assert response.get_json()["error"]["details"] == {"field": "puntuacion"}


def test_unexpected_error_returns_500(client, app, monkeypatch):
    app.config["TESTING"] = False
    app.config["PROPAGATE_EXCEPTIONS"] = False

    def _boom(**kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(app.config["support_service"], "create_rating", _boom)

    response = _create_rating(client)

    assert response.status_code == 500
    assert response.get_json()["error"]["code"] == "internal_server_error"
