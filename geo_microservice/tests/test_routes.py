from __future__ import annotations

from unittest import mock

from app.geocoding_service import GeocodedLocation


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200


@mock.patch("app.api.routes.GeocodingService.geocode_address")
def test_geocode_get(geocode_address, client):
    from decimal import Decimal

    geocode_address.return_value = GeocodedLocation(
        latitud=Decimal("6.2"), longitud=Decimal("-75.5"), direccion_texto="X"
    )
    response = client.get("/geocode", query_string={"direccion_texto": "Calle 1"})
    assert response.status_code == 200
    assert response.get_json()["direccion_texto"] == "X"


@mock.patch("app.api.routes.GeocodingService.geocode_address")
def test_geocode_post_uses_q_fallback(geocode_address, client):
    from decimal import Decimal

    geocode_address.return_value = GeocodedLocation(
        latitud=Decimal("6.2"), longitud=Decimal("-75.5"), direccion_texto="X"
    )
    response = client.post("/geocode", json={"q": "Calle 1"})
    assert response.status_code == 200
    geocode_address.assert_called_once_with(direccion_texto="Calle 1")


def test_geocode_requires_address(client):
    response = client.get("/geocode")
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "validation_error"


def test_geocode_v2_alias(client):
    with mock.patch("app.api.routes.GeocodingService.geocode_address") as geocode_address:
        from decimal import Decimal

        geocode_address.return_value = GeocodedLocation(
            latitud=Decimal("1"), longitud=Decimal("1"), direccion_texto="X"
        )
        response = client.get("/api/v2/geocode", query_string={"direccion_texto": "x"})
    assert response.status_code == 200


@mock.patch("app.api.routes.GeocodingService.suggest_addresses")
def test_suggest_get(suggest_addresses, client):
    suggest_addresses.return_value = [{"primary": "X"}]
    response = client.get("/geocode/suggest", query_string={"q": "algo"})
    assert response.status_code == 200
    assert response.get_json()["items"] == [{"primary": "X"}]


def test_suggest_invalid_limit_returns_400(client):
    response = client.get("/geocode/suggest", query_string={"q": "algo", "limit": "abc"})
    assert response.status_code == 400


@mock.patch("app.api.routes.GeocodingService.suggest_addresses")
def test_suggest_default_limit(suggest_addresses, client):
    suggest_addresses.return_value = []
    client.get("/geocode/suggest", query_string={"q": "algo"})
    suggest_addresses.assert_called_once_with(query="algo", limit=5)


def test_route_requires_coords(client):
    response = client.get("/route")
    assert response.status_code == 400


@mock.patch("app.api.routes.RouteService.get_route")
def test_route_success(get_route, client):
    get_route.return_value = {"duration": 1.0, "distance": 2.0, "geometry": [], "legs": []}
    response = client.get("/route", query_string={"coords": "0,0;1,1"})
    assert response.status_code == 200
    assert response.get_json()["distance"] == 2.0


@mock.patch("app.api.routes.RouteService.get_route")
def test_route_returns_502_when_no_route_found(get_route, client):
    get_route.return_value = None
    response = client.get("/route", query_string={"coords": "0,0;1,1"})
    assert response.status_code == 502


@mock.patch("app.api.routes.RouteService.get_route")
def test_route_post(get_route, client):
    get_route.return_value = {"duration": 1.0, "distance": 2.0, "geometry": [], "legs": []}
    response = client.post("/route", json={"coords": "0,0;1,1"})
    assert response.status_code == 200


def test_api_error_with_details_included_in_response(client):
    from app.errors import ValidationError

    with mock.patch(
        "app.api.routes.GeocodingService.geocode_address",
        side_effect=ValidationError("invalido", details={"field": "direccion_texto"}),
    ):
        response = client.get("/geocode", query_string={"direccion_texto": "x"})
    assert response.status_code == 400
    assert response.get_json()["error"]["details"] == {"field": "direccion_texto"}


def test_unexpected_error_returns_500(client, app):
    app.config["TESTING"] = False
    app.config["PROPAGATE_EXCEPTIONS"] = False
    with mock.patch(
        "app.api.routes.GeocodingService.geocode_address", side_effect=RuntimeError("boom")
    ):
        response = client.get("/geocode", query_string={"direccion_texto": "x"})
    assert response.status_code == 500
    assert response.get_json()["error"]["code"] == "internal_server_error"
