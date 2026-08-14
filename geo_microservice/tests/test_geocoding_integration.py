from __future__ import annotations

from unittest import mock
from urllib.error import HTTPError

import pytest

from app.errors import ValidationError
from app.geocoding_service import GeocodingService


def test_geocode_address_requires_non_blank():
    with pytest.raises(ValidationError):
        GeocodingService().geocode_address(direccion_texto="   ")


def test_geocode_address_poi_shortcut_skips_network():
    with mock.patch.object(GeocodingService, "_fetch_json") as fetch_json:
        loc = GeocodingService().geocode_address(direccion_texto="Universidad EAFIT")
    fetch_json.assert_not_called()
    assert "EAFIT" in loc.direccion_texto


@mock.patch("app.geocoding_service.GeocodingService._fetch_json")
def test_geocode_address_nominatim_success(fetch_json):
    fetch_json.return_value = [{"lat": "6.25", "lon": "-75.56", "display_name": "Medellin, Antioquia"}]

    loc = GeocodingService().geocode_address(direccion_texto="Calle 10 #20-30, Medellin")

    assert loc.direccion_texto == "Medellin, Antioquia"
    assert fetch_json.call_count == 1


@mock.patch("app.geocoding_service.GeocodingService._fetch_json")
def test_geocode_address_uses_cache_on_second_call(fetch_json):
    fetch_json.return_value = [{"lat": "6.25", "lon": "-75.56", "display_name": "X, Medellin"}]

    GeocodingService().geocode_address(direccion_texto="Calle 10 unico geo, Medellin")
    GeocodingService().geocode_address(direccion_texto="Calle 10 unico geo, Medellin")

    assert fetch_json.call_count == 1


@mock.patch("app.geocoding_service.GeocodingService._fetch_json")
def test_geocode_address_falls_back_to_variant_for_colombia(fetch_json):
    calls = []

    def side_effect(url, **kwargs):
        calls.append(url)
        # La query principal (con "-125") falla; solo la variante generalizada
        # (sin el tramo final "-125") devuelve resultado.
        if "125" in url:
            return []
        return [{"lat": "6.2", "lon": "-75.5", "display_name": "Zona aproximada, Medellin"}]

    fetch_json.side_effect = side_effect

    loc = GeocodingService().geocode_address(direccion_texto="Calle 5 #80C-125, Medellin")
    assert loc.direccion_texto == "Zona aproximada, Medellin"
    assert len(calls) >= 2


@mock.patch("app.geocoding_service.GeocodingService._fetch_json", return_value=[])
def test_geocode_address_no_results_anywhere_raises(fetch_json):
    with pytest.raises(ValidationError):
        GeocodingService().geocode_address(direccion_texto="Calle inexistente #1-1, Medellin")


@mock.patch("app.geocoding_service.GeocodingService._fetch_json")
def test_geocode_address_missing_lat_lon_returns_none(fetch_json):
    fetch_json.return_value = [{"display_name": "Sin coords"}]
    with pytest.raises(ValidationError):
        GeocodingService().geocode_address(direccion_texto="Paris, France")


def test_nominatim_geocode_respects_backoff(monkeypatch):
    import time

    monkeypatch.setattr(GeocodingService, "_nominatim_backoff_until", time.time() + 100)
    with mock.patch.object(GeocodingService, "_fetch_json") as fetch_json:
        result = GeocodingService()._nominatim_geocode("Paris")
    fetch_json.assert_not_called()
    assert result is None


def test_suggest_addresses_requires_non_blank():
    with pytest.raises(ValidationError):
        GeocodingService().suggest_addresses(query="   ")


def test_suggest_addresses_poi_shortcut():
    items = GeocodingService().suggest_addresses(query="eafit", limit=5)
    assert len(items) == 1
    assert items[0]["primary"] == "Universidad EAFIT"


@mock.patch("app.geocoding_service.GeocodingService._fetch_json")
def test_suggest_addresses_global_query(fetch_json):
    fetch_json.return_value = [
        {"display_name": "Paris, France", "lat": "48.8", "lon": "2.3", "address": {"city": "Paris"}}
    ]
    items = GeocodingService().suggest_addresses(query="Paris", limit=5)
    assert len(items) == 1
    assert items[0]["primary"]


@mock.patch("app.geocoding_service.GeocodingService._fetch_json")
def test_suggest_addresses_uses_cache_on_second_call(fetch_json):
    fetch_json.return_value = [{"display_name": "X, Paris", "lat": "1", "lon": "1"}]
    GeocodingService().suggest_addresses(query="query unico suggest", limit=5)
    GeocodingService().suggest_addresses(query="query unico suggest", limit=5)
    assert fetch_json.call_count == 1


@mock.patch("app.geocoding_service.GeocodingService._fetch_json")
def test_suggest_addresses_colombia_house_detail_variants(fetch_json):
    fetch_json.return_value = [
        {
            "display_name": "Calle 5 #80C-125, El Poblado, Medellin, Antioquia",
            "lat": "6.2",
            "lon": "-75.5",
            "address": {"road": "Calle 5", "house_number": "80C-125", "city": "Medellin", "state": "Antioquia"},
        }
    ]
    items = GeocodingService().suggest_addresses(query="Calle 5 #80C-125", limit=5)
    assert len(items) == 1
    assert items[0]["primary"] == "Calle 5 #80C-125"


@mock.patch("app.geocoding_service.GeocodingService._fetch_json", return_value=[])
def test_suggest_addresses_no_results_returns_empty(fetch_json):
    items = GeocodingService().suggest_addresses(query="direccion sin resultados #1-1", limit=5)
    assert items == []


def test_fetch_json_success():
    response = mock.MagicMock()
    response.read.return_value = b'[{"lat": "1"}]'
    response.__enter__.return_value = response
    with mock.patch("app.geocoding_service.urlopen", return_value=response):
        result = GeocodingService._fetch_json("https://example.com", headers={})
    assert result == [{"lat": "1"}]


def test_fetch_json_rate_limited_sets_backoff():
    error = HTTPError("https://nominatim.openstreetmap.org/search", 429, "Too Many Requests", {}, None)
    with mock.patch("app.geocoding_service.urlopen", side_effect=error):
        with pytest.raises(ValidationError):
            GeocodingService._fetch_json("https://nominatim.openstreetmap.org/search?q=x", headers={})
    assert GeocodingService._nominatim_backoff_until > 0


def test_fetch_json_other_http_error_does_not_set_backoff():
    error = HTTPError("https://nominatim.openstreetmap.org/search", 500, "Server Error", {}, None)
    with mock.patch("app.geocoding_service.urlopen", side_effect=error):
        with pytest.raises(ValidationError):
            GeocodingService._fetch_json("https://nominatim.openstreetmap.org/search?q=x", headers={})
    assert GeocodingService._nominatim_backoff_until == 0.0


def test_fetch_json_generic_exception_raises_validation_error():
    with mock.patch("app.geocoding_service.urlopen", side_effect=OSError("boom")):
        with pytest.raises(ValidationError):
            GeocodingService._fetch_json("https://example.com", headers={})


def test_nominatim_search_swallows_validation_error():
    with mock.patch.object(GeocodingService, "_fetch_json", side_effect=ValidationError("boom")):
        result = GeocodingService()._nominatim_search("algo")
    assert result == []


def test_nominatim_search_returns_empty_for_non_list_payload():
    with mock.patch.object(GeocodingService, "_fetch_json", return_value={"not": "a list"}):
        result = GeocodingService()._nominatim_search("algo")
    assert result == []


def test_nominatim_search_respects_backoff(monkeypatch):
    import time

    monkeypatch.setattr(GeocodingService, "_nominatim_backoff_until", time.time() + 100)
    with mock.patch.object(GeocodingService, "_fetch_json") as fetch_json:
        result = GeocodingService()._nominatim_search("algo")
    fetch_json.assert_not_called()
    assert result == []
