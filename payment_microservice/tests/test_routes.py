from __future__ import annotations


def _create_payment(client, **overrides):
    payload = {
        "usuario_id": 1, "pedido_id": "77", "monto": "20000",
        "metodo_pago": "credit_card", "moneda": "COP",
    }
    payload.update(overrides)
    return client.post("/api/v2/payments", json=payload)


def test_health_check(client):
    assert client.get("/health").status_code == 200


def test_create_payment_success(client):
    response = _create_payment(client)
    assert response.status_code == 201
    data = response.get_json()["data"]
    assert data["estado"] == "AUTORIZADO"


def test_create_payment_non_json_body_returns_400(client):
    response = client.post("/api/v2/payments", data="not json", content_type="text/plain")
    assert response.status_code == 400


def test_create_payment_validation_error_returns_400_with_details(client):
    response = _create_payment(client, usuario_id=-1)
    assert response.status_code == 400
    assert "usuario_id" in response.get_json()["error"]["details"]


def test_create_payment_declined_over_limit(client):
    response = _create_payment(client, monto="20000000")
    assert response.status_code == 201
    assert response.get_json()["data"]["estado"] == "FALLIDO"


def test_get_payment_success(client):
    payment_id = _create_payment(client).get_json()["data"]["id"]
    response = client.get(f"/api/v2/payments/{payment_id}")
    assert response.status_code == 200
    assert response.get_json()["data"]["id"] == payment_id


def test_get_payment_not_found_returns_404(client):
    response = client.get("/api/v2/payments/no-existe")
    assert response.status_code == 404


def test_unknown_route_returns_404_via_http_exception_handler(client):
    response = client.get("/api/v2/does-not-exist")
    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "not_found"


def test_unexpected_error_returns_500(client, app, monkeypatch):
    app.config["TESTING"] = False
    app.config["PROPAGATE_EXCEPTIONS"] = False

    def _boom(**kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(app.config["payment_service"], "create_payment", _boom)

    response = _create_payment(client)

    assert response.status_code == 500
    assert response.get_json()["error"]["code"] == "internal_server_error"
