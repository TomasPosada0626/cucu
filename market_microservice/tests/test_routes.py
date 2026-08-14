from __future__ import annotations



def _create_publication(client, **overrides):
    payload = {
        "autor_id": 1, "titulo": "Sopa", "descripcion": "Rica", "precio": 10.0, "direccion_texto": "Calle 1",
    }
    payload.update(overrides)
    return client.post("/api/v3/publications", json=payload)


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200


def test_create_publication_success(client):
    response = _create_publication(client)
    assert response.status_code == 201
    assert response.get_json()["data"]["titulo"] == "Sopa"


def test_create_publication_non_json_body_returns_400(client):
    response = client.post("/api/v3/publications", data="not json", content_type="text/plain")
    assert response.status_code == 400


def test_create_publication_invalid_autor_returns_400(client):
    response = _create_publication(client, autor_id=0)
    assert response.status_code == 400


def test_list_publications(client):
    _create_publication(client, titulo="A")
    _create_publication(client, titulo="B")
    response = client.get("/api/v3/publications")
    assert response.status_code == 200
    assert len(response.get_json()["data"]) == 2


def test_create_order_success(client):
    pub_id = _create_publication(client).get_json()["data"]["id"]
    response = client.post(
        "/api/v3/orders", json={"publicacion_id": pub_id, "comprador_id": 5, "cantidad": 2}
    )
    assert response.status_code == 201
    body = response.get_json()["data"]
    assert body["cantidad"] == 2
    assert body["total"] == 20.0


def test_create_order_publication_not_found_returns_404(client):
    response = client.post(
        "/api/v3/orders", json={"publicacion_id": 999999, "comprador_id": 1, "cantidad": 1}
    )
    assert response.status_code == 404


def test_create_order_invalid_cantidad_returns_400(client):
    pub_id = _create_publication(client).get_json()["data"]["id"]
    response = client.post(
        "/api/v3/orders", json={"publicacion_id": pub_id, "comprador_id": 1, "cantidad": 0}
    )
    assert response.status_code == 400


def test_list_orders(client):
    pub_id = _create_publication(client).get_json()["data"]["id"]
    client.post("/api/v3/orders", json={"publicacion_id": pub_id, "comprador_id": 1, "cantidad": 1})
    response = client.get("/api/v3/orders")
    assert response.status_code == 200
    assert len(response.get_json()["data"]) == 1


def test_get_order_success(client):
    pub_id = _create_publication(client).get_json()["data"]["id"]
    order_id = client.post(
        "/api/v3/orders", json={"publicacion_id": pub_id, "comprador_id": 1, "cantidad": 1}
    ).get_json()["data"]["id"]

    response = client.get(f"/api/v3/orders/{order_id}")

    assert response.status_code == 200
    assert response.get_json()["data"]["id"] == order_id


def test_get_order_not_found_returns_404(client):
    response = client.get("/api/v3/orders/999999")
    assert response.status_code == 404


def test_api_error_with_details_included_in_response(client, app, monkeypatch):
    from app.errors import ValidationError

    def _boom(**kwargs):
        raise ValidationError("invalido", details={"field": "titulo"})

    monkeypatch.setattr(app.config["market_service"], "create_publication", _boom)

    response = _create_publication(client)

    assert response.status_code == 400
    assert response.get_json()["error"]["details"] == {"field": "titulo"}


def test_unexpected_error_returns_500(client, app, monkeypatch):
    app.config["TESTING"] = False
    app.config["PROPAGATE_EXCEPTIONS"] = False

    def _boom(**kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(app.config["market_service"], "list_publications", _boom)

    response = client.get("/api/v3/publications")

    assert response.status_code == 500
    assert response.get_json()["error"]["code"] == "internal_server_error"
