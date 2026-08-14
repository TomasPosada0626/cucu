from __future__ import annotations

from unittest import mock

from app.routing_service import RouteService, _decode_polyline6

# Verificado contra la funcion real de decodificacion: decodifica a
# [[-74.08, 4.65], [-74.09, 4.66], [-74.1, 4.7]] (lon, lat).
POLYLINE6_FIXTURE = "_`yzG~nnhlC_pR~oR_cmA~oR"
POLYLINE6_FIXTURE_CONTINUATION = "_uz}G~puilC_t`B~`f@"


def test_decode_polyline6_matches_expected_points():
    assert _decode_polyline6(POLYLINE6_FIXTURE) == [[-74.08, 4.65], [-74.09, 4.66], [-74.1, 4.7]]


def test_get_route_returns_none_when_all_providers_fail():
    service = RouteService()
    with mock.patch.object(RouteService, "_fetch_osrm_route", return_value=None), \
            mock.patch.object(RouteService, "_fetch_valhalla_route", return_value=None):
        assert service.get_route(coords="-74.08,4.65;-74.09,4.66") is None


def test_get_route_prefers_osrm_when_available():
    service = RouteService()
    payload = {
        "code": "Ok",
        "routes": [{
            "duration": 100.0,
            "distance": 200.0,
            "geometry": {"coordinates": [[-74.08, 4.65], [-74.09, 4.66]]},
            "legs": [{"duration": 100.0, "distance": 200.0}],
        }],
    }
    with mock.patch("app.routing_service._fetch_json", return_value=payload):
        route = service.get_route(coords="-74.08,4.65;-74.09,4.66")
    assert route["distance"] == 200.0


def test_get_route_falls_back_to_valhalla_when_osrm_fails():
    service = RouteService()
    payload = {
        "trip": {
            "status": 0,
            "legs": [{"shape": POLYLINE6_FIXTURE, "summary": {"time": 30, "length": 1.2}}],
        }
    }
    with mock.patch.object(RouteService, "_fetch_osrm_route", return_value=None), \
            mock.patch("app.routing_service._fetch_json", return_value=payload):
        route = service.get_route(coords="-74.08,4.65;-74.1,4.7")
    assert route["duration"] == 30
    assert route["distance"] == 1200.0


def test_get_route_provider_exception_is_swallowed():
    service = RouteService()
    with mock.patch.object(RouteService, "_fetch_osrm_route", side_effect=RuntimeError("boom")), \
            mock.patch.object(RouteService, "_fetch_valhalla_route", return_value=None):
        assert service.get_route(coords="0,0;1,1") is None


def test_osrm_route_returns_none_when_code_not_ok():
    service = RouteService()
    with mock.patch("app.routing_service._fetch_json", return_value={"code": "NoRoute"}):
        assert service._fetch_osrm_route("0,0;1,1") is None


def test_osrm_route_returns_none_when_no_routes():
    service = RouteService()
    with mock.patch("app.routing_service._fetch_json", return_value={"code": "Ok", "routes": []}):
        assert service._fetch_osrm_route("0,0;1,1") is None


def test_osrm_route_returns_none_when_no_geometry():
    service = RouteService()
    payload = {"code": "Ok", "routes": [{"geometry": {}}]}
    with mock.patch("app.routing_service._fetch_json", return_value=payload):
        assert service._fetch_osrm_route("0,0;1,1") is None


def test_valhalla_route_bad_status_returns_none():
    service = RouteService()
    with mock.patch("app.routing_service._fetch_json", return_value={"trip": {"status": 1}}):
        assert service._fetch_valhalla_route("0,0;1,1") is None


def test_valhalla_route_no_legs_returns_none():
    service = RouteService()
    payload = {"trip": {"status": 0, "legs": []}}
    with mock.patch("app.routing_service._fetch_json", return_value=payload):
        assert service._fetch_valhalla_route("0,0;1,1") is None


def test_valhalla_route_empty_shape_returns_none():
    service = RouteService()
    payload = {"trip": {"status": 0, "legs": [{"shape": "", "summary": {}}]}}
    with mock.patch("app.routing_service._fetch_json", return_value=payload):
        assert service._fetch_valhalla_route("0,0;1,1") is None


def test_valhalla_route_merges_consecutive_legs():
    service = RouteService()
    payload = {
        "trip": {
            "status": 0,
            "legs": [
                {"shape": POLYLINE6_FIXTURE, "summary": {"time": 10, "length": 1}},
                {"shape": POLYLINE6_FIXTURE_CONTINUATION, "summary": {"time": 20, "length": 2}},
            ],
        }
    }
    with mock.patch("app.routing_service._fetch_json", return_value=payload):
        route = service._fetch_valhalla_route("0,0;1,1")
    assert len(route["geometry"]) == 4


def test_module_fetch_json_parses_response():
    from app.routing_service import _fetch_json as real_fetch_json

    response = mock.MagicMock()
    response.read.return_value = b'{"code": "Ok"}'
    response.__enter__.return_value = response
    with mock.patch("app.routing_service.urlopen", return_value=response):
        assert real_fetch_json("https://example.com", headers={}, timeout=1) == {"code": "Ok"}
