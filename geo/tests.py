import os
from decimal import Decimal
from unittest import mock

from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.infrastructure.models import User
from common.exceptions import ValidationError

from .domain.services import GeocodedLocation, GeocodingService
from .infrastructure.models import Ubicacion
from .infrastructure.routing import RouteService, _decode_polyline5, _decode_polyline6
from .interfaces.serializers.geo_serializer import (
    GeocodeQuerySerializer,
    GeocodeSuggestQuerySerializer,
    ReverseGeocodeQuerySerializer,
    RouteQuerySerializer,
)

# Cadenas de polyline verificadas contra las funciones reales de decodificacion
# (ver _decode_polyline5/_decode_polyline6) para los puntos
# [(-74.08, 4.65), (-74.09, 4.66), (-74.1, 4.7)] en formato [lon, lat].
POLYLINE5_FIXTURE = "oek[~vccMo}@n}@_yFn}@"
POLYLINE6_FIXTURE = "_`yzG~nnhlC_pR~oR_cmA~oR"
# Continua justo donde termina POLYLINE6_FIXTURE: (-74.1, 4.7) -> (-74.12, 4.75)
POLYLINE6_FIXTURE_CONTINUATION = "_uz}G~puilC_t`B~`f@"


class UbicacionModelTests(TestCase):
    def test_str_includes_direccion_and_coords(self):
        ubicacion = Ubicacion.objects.create(
            direccion_texto="Calle 10, Bogota", latitud="4.65", longitud="-74.08"
        )
        self.assertIn("Calle 10, Bogota", str(ubicacion))
        self.assertIn("4.65", str(ubicacion))


class GeoSerializerTests(TestCase):
    def test_geocode_query_falls_back_to_q_when_direccion_texto_missing(self):
        serializer = GeocodeQuerySerializer(data={"q": " Calle 10 "})
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["direccion_texto"], "Calle 10")

    def test_geocode_query_prefers_direccion_texto_over_q(self):
        serializer = GeocodeQuerySerializer(data={"direccion_texto": "Principal", "q": "Otra"})
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["direccion_texto"], "Principal")

    def test_geocode_query_requires_some_address(self):
        serializer = GeocodeQuerySerializer(data={})
        self.assertFalse(serializer.is_valid())

    def test_geocode_suggest_query_requires_q(self):
        serializer = GeocodeSuggestQuerySerializer(data={})
        self.assertFalse(serializer.is_valid())

    def test_geocode_suggest_query_limit_bounds(self):
        serializer = GeocodeSuggestQuerySerializer(data={"q": "pizza", "limit": 20})
        self.assertFalse(serializer.is_valid())

    def test_reverse_geocode_query_requires_bounds(self):
        serializer = ReverseGeocodeQuerySerializer(data={"latitud": 200, "longitud": 0})
        self.assertFalse(serializer.is_valid())

    def test_reverse_geocode_query_valid(self):
        serializer = ReverseGeocodeQuerySerializer(data={"latitud": 4.6, "longitud": -74.08})
        self.assertTrue(serializer.is_valid())

    def test_route_query_requires_coords(self):
        serializer = RouteQuerySerializer(data={})
        self.assertFalse(serializer.is_valid())


class GeocodingServiceTests(TestCase):
    def setUp(self):
        GeocodingService._geocode_cache.clear()
        GeocodingService._suggest_cache.clear()

    def test_geocode_address_requires_non_blank_text(self):
        with self.assertRaises(ValidationError):
            GeocodingService().geocode_address(direccion_texto="   ")

    @mock.patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": ""})
    def test_geocode_address_without_api_key_raises(self):
        with self.assertRaises(ValidationError):
            GeocodingService().geocode_address(direccion_texto="Calle 10")

    @mock.patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "test-key"})
    @mock.patch("geo.domain.services.GeocodingService._fetch_json")
    def test_geocode_address_success_and_caches(self, fetch_json):
        fetch_json.return_value = {
            "status": "OK",
            "results": [{
                "formatted_address": "Calle 10 # 20-30, Bogota",
                "geometry": {"location": {"lat": 4.65, "lng": -74.08}},
            }],
        }
        service = GeocodingService()
        loc = service.geocode_address(direccion_texto="Calle 10 unico test")
        self.assertEqual(loc.direccion_texto, "Calle 10 # 20-30, Bogota")
        self.assertEqual(float(loc.latitud), 4.65)

        service.geocode_address(direccion_texto="Calle 10 unico test")
        self.assertEqual(fetch_json.call_count, 1)

    @mock.patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "test-key"})
    @mock.patch("geo.domain.services.GeocodingService._fetch_json")
    def test_geocode_address_no_results_raises(self, fetch_json):
        fetch_json.return_value = {"status": "ZERO_RESULTS", "results": []}
        with self.assertRaises(ValidationError):
            GeocodingService().geocode_address(direccion_texto="direccion inexistente xyz")

    @mock.patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "test-key"})
    @mock.patch("geo.domain.services.GeocodingService._fetch_json")
    def test_geocode_address_missing_lat_lng_raises(self, fetch_json):
        fetch_json.return_value = {
            "status": "OK",
            "results": [{"formatted_address": "X", "geometry": {"location": {}}}],
        }
        with self.assertRaises(ValidationError):
            GeocodingService().geocode_address(direccion_texto="direccion sin coords")

    @mock.patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "test-key"})
    @mock.patch("geo.domain.services.GeocodingService._fetch_json")
    def test_reverse_geocode_success(self, fetch_json):
        fetch_json.return_value = {
            "status": "OK",
            "results": [{"formatted_address": "Calle 10, Bogota"}],
        }
        loc = GeocodingService().reverse_geocode(latitud=4.65, longitud=-74.08)
        self.assertEqual(loc.direccion_texto, "Calle 10, Bogota")

    @mock.patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "test-key"})
    @mock.patch("geo.domain.services.GeocodingService._fetch_json")
    def test_reverse_geocode_no_results_raises(self, fetch_json):
        fetch_json.return_value = {"status": "OK", "results": []}
        with self.assertRaises(ValidationError):
            GeocodingService().reverse_geocode(latitud=4.65, longitud=-74.08)

    @mock.patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "test-key"})
    @mock.patch("geo.domain.services.GeocodingService._fetch_json")
    def test_reverse_geocode_bad_status_raises(self, fetch_json):
        fetch_json.return_value = None
        with self.assertRaises(ValidationError):
            GeocodingService().reverse_geocode(latitud=4.65, longitud=-74.08)

    def test_suggest_addresses_requires_non_blank_query(self):
        with self.assertRaises(ValidationError):
            GeocodingService().suggest_addresses(query="  ")

    @mock.patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "test-key"})
    @mock.patch("geo.domain.services.GeocodingService._fetch_json")
    def test_suggest_addresses_success_and_caches(self, fetch_json):
        fetch_json.return_value = {
            "status": "OK",
            "results": [
                {
                    "name": "Restaurante A", "formatted_address": "Calle 1",
                    "geometry": {"location": {"lat": 4.6, "lng": -74.1}},
                },
                {"name": "Sin coords", "formatted_address": "Calle 2", "geometry": {}},
            ],
        }
        service = GeocodingService()
        items = service.suggest_addresses(query="restaurante unico", limit=5)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["primary"], "Restaurante A")

        service.suggest_addresses(query="restaurante unico", limit=5)
        self.assertEqual(fetch_json.call_count, 1)

    @mock.patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "test-key"})
    @mock.patch("geo.domain.services.GeocodingService._fetch_json")
    def test_suggest_addresses_zero_results_returns_empty_list(self, fetch_json):
        fetch_json.return_value = {"status": "ZERO_RESULTS", "results": []}
        items = GeocodingService().suggest_addresses(query="nada por aqui")
        self.assertEqual(items, [])

    @mock.patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "test-key"})
    @mock.patch("geo.domain.services.GeocodingService._fetch_json")
    def test_suggest_addresses_bad_status_returns_empty_list(self, fetch_json):
        fetch_json.return_value = {"status": "REQUEST_DENIED"}
        items = GeocodingService().suggest_addresses(query="algo")
        self.assertEqual(items, [])

    def test_fetch_json_returns_none_on_network_error(self):
        with mock.patch("geo.domain.services.urlopen", side_effect=OSError("boom")):
            result = GeocodingService._fetch_json("https://example.com")
        self.assertIsNone(result)

    def test_fetch_json_parses_successful_response(self):
        response = mock.MagicMock()
        response.read.return_value = b'{"status": "OK"}'
        response.__enter__.return_value = response
        with mock.patch("geo.domain.services.urlopen", return_value=response):
            result = GeocodingService._fetch_json("https://example.com")
        self.assertEqual(result, {"status": "OK"})

    @mock.patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "test-key"})
    @mock.patch("geo.domain.services.GeocodingService._fetch_json")
    def test_geocode_address_ok_status_no_results_raises(self, fetch_json):
        fetch_json.return_value = {"status": "OK", "results": []}
        with self.assertRaises(ValidationError):
            GeocodingService().geocode_address(direccion_texto="direccion sin resultados")

    def test_geocode_cache_expired_entry_is_treated_as_miss(self):
        GeocodingService._geocode_cache["clave expirada"] = (0.0, mock.sentinel.stale)
        self.assertIsNone(GeocodingService._geocode_cache_get("clave expirada"))
        self.assertNotIn("clave expirada", GeocodingService._geocode_cache)

    def test_geocode_cache_clears_when_full(self):
        with mock.patch.object(GeocodingService, "_GEOCODE_CACHE_MAX", 1):
            GeocodingService._geocode_cache_set("primero", mock.sentinel.a)
            GeocodingService._geocode_cache_set("segundo", mock.sentinel.b)
        self.assertNotIn("primero", GeocodingService._geocode_cache)
        self.assertIn("segundo", GeocodingService._geocode_cache)

    def test_suggest_cache_expired_entry_is_treated_as_miss(self):
        key = ("clave expirada", 5)
        GeocodingService._suggest_cache[key] = (0.0, [])
        self.assertIsNone(GeocodingService._suggest_cache_get(key))
        self.assertNotIn(key, GeocodingService._suggest_cache)

    def test_suggest_cache_clears_when_full(self):
        with mock.patch.object(GeocodingService, "_SUGGEST_CACHE_MAX", 1):
            GeocodingService._suggest_cache_set(("primero", 5), [])
            GeocodingService._suggest_cache_set(("segundo", 5), [])
        self.assertNotIn(("primero", 5), GeocodingService._suggest_cache)
        self.assertIn(("segundo", 5), GeocodingService._suggest_cache)


class RouteServiceTests(TestCase):
    def setUp(self):
        self.service = RouteService()

    def test_get_route_returns_none_when_all_providers_fail(self):
        with mock.patch.object(RouteService, "_fetch_google_route", return_value=None), \
                mock.patch.object(RouteService, "_fetch_osrm_route", return_value=None), \
                mock.patch.object(RouteService, "_fetch_valhalla_route", return_value=None):
            self.assertIsNone(self.service.get_route(coords="-74.08,4.65;-74.09,4.66"))

    def test_get_route_falls_back_to_osrm_when_google_key_missing(self):
        with mock.patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": ""}), \
                mock.patch("geo.infrastructure.routing._fetch_json") as fetch_json:
            fetch_json.return_value = {
                "code": "Ok",
                "routes": [{
                    "duration": 120.5,
                    "distance": 950.0,
                    "geometry": {"coordinates": [[-74.08, 4.65], [-74.09, 4.66]]},
                    "legs": [{"duration": 120.5, "distance": 950.0}],
                }],
            }
            route = self.service.get_route(coords="-74.08,4.65;-74.09,4.66")
        self.assertIsNotNone(route)
        self.assertEqual(route["distance"], 950.0)
        self.assertEqual(len(route["legs"]), 1)

    def test_get_route_provider_exception_is_swallowed_and_tries_next(self):
        with mock.patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "test-key"}), \
                mock.patch.object(RouteService, "_fetch_google_route", side_effect=RuntimeError("boom")), \
                mock.patch("geo.infrastructure.routing._fetch_json") as fetch_json:
            fetch_json.return_value = {
                "code": "Ok",
                "routes": [{
                    "duration": 10.0, "distance": 5.0,
                    "geometry": {"coordinates": [[0, 0]]},
                    "legs": [],
                }],
            }
            route = self.service.get_route(coords="0,0;1,1")
        self.assertIsNotNone(route)

    def test_osrm_route_returns_none_when_code_not_ok(self):
        with mock.patch("geo.infrastructure.routing._fetch_json", return_value={"code": "NoRoute"}):
            self.assertIsNone(self.service._fetch_osrm_route("0,0;1,1"))

    def test_osrm_route_returns_none_when_no_geometry(self):
        payload = {"code": "Ok", "routes": [{"geometry": {}}]}
        with mock.patch("geo.infrastructure.routing._fetch_json", return_value=payload):
            self.assertIsNone(self.service._fetch_osrm_route("0,0;1,1"))

    @mock.patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "test-key"})
    def test_google_route_decodes_polyline_and_sums_legs(self):
        payload = {
            "status": "OK",
            "routes": [{
                "overview_polyline": {"points": POLYLINE5_FIXTURE},
                "legs": [
                    {"duration": {"value": 100}, "distance": {"value": 200}},
                    {"duration": {"value": 50}, "distance": {"value": 150}},
                ],
            }],
        }
        with mock.patch("geo.infrastructure.routing._fetch_json", return_value=payload):
            route = self.service._fetch_google_route("-74.08,4.65;-74.1,4.7")
        self.assertIsNotNone(route)
        self.assertEqual(route["duration"], 150)
        self.assertEqual(route["distance"], 350)
        self.assertEqual(len(route["geometry"]), 3)

    def test_google_route_without_api_key_returns_none(self):
        with mock.patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": ""}):
            self.assertIsNone(self.service._fetch_google_route("-74.08,4.65;-74.1,4.7"))

    @mock.patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "test-key"})
    def test_google_route_needs_at_least_two_points(self):
        self.assertIsNone(self.service._fetch_google_route("-74.08,4.65"))

    @mock.patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "test-key"})
    def test_google_route_with_waypoints(self):
        payload = {
            "status": "OK",
            "routes": [{
                "overview_polyline": {"points": POLYLINE5_FIXTURE},
                "legs": [{"duration": {"value": 10}, "distance": {"value": 20}}],
            }],
        }
        with mock.patch("geo.infrastructure.routing._fetch_json", return_value=payload) as fetch_json:
            route = self.service._fetch_google_route("-74.08,4.65;-74.09,4.66;-74.1,4.7")
        self.assertIsNotNone(route)
        called_url = fetch_json.call_args[0][0]
        self.assertIn("waypoints", called_url)

    @mock.patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "test-key"})
    def test_google_route_bad_status_returns_none(self):
        with mock.patch("geo.infrastructure.routing._fetch_json", return_value={"status": "ZERO_RESULTS"}):
            self.assertIsNone(self.service._fetch_google_route("-74.08,4.65;-74.1,4.7"))

    def test_valhalla_route_decodes_shape_and_sums_legs(self):
        payload = {
            "trip": {
                "status": 0,
                "legs": [
                    {"shape": POLYLINE6_FIXTURE, "summary": {"time": 30, "length": 1.2}},
                ],
            }
        }
        with mock.patch("geo.infrastructure.routing._fetch_json", return_value=payload):
            route = self.service._fetch_valhalla_route("-74.08,4.65;-74.1,4.7")
        self.assertIsNotNone(route)
        self.assertEqual(route["duration"], 30)
        self.assertEqual(route["distance"], 1200.0)

    def test_valhalla_route_bad_status_returns_none(self):
        with mock.patch("geo.infrastructure.routing._fetch_json", return_value={"trip": {"status": 1}}):
            self.assertIsNone(self.service._fetch_valhalla_route("-74.08,4.65;-74.1,4.7"))

    def test_valhalla_route_no_legs_returns_none(self):
        payload = {"trip": {"status": 0, "legs": []}}
        with mock.patch("geo.infrastructure.routing._fetch_json", return_value=payload):
            self.assertIsNone(self.service._fetch_valhalla_route("-74.08,4.65;-74.1,4.7"))

    def test_module_fetch_json_parses_successful_response(self):
        from geo.infrastructure.routing import _fetch_json as real_fetch_json

        response = mock.MagicMock()
        response.read.return_value = b'{"code": "Ok"}'
        response.__enter__.return_value = response
        with mock.patch("geo.infrastructure.routing.urlopen", return_value=response):
            result = real_fetch_json("https://example.com", headers={}, timeout=1)
        self.assertEqual(result, {"code": "Ok"})

    @mock.patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "test-key"})
    def test_google_route_no_routes_returns_none(self):
        with mock.patch("geo.infrastructure.routing._fetch_json", return_value={"status": "OK", "routes": []}):
            self.assertIsNone(self.service._fetch_google_route("-74.08,4.65;-74.1,4.7"))

    @mock.patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "test-key"})
    def test_google_route_without_overview_polyline_returns_none(self):
        payload = {
            "status": "OK",
            "routes": [{"legs": [{"duration": {"value": 10}, "distance": {"value": 20}}]}],
        }
        with mock.patch("geo.infrastructure.routing._fetch_json", return_value=payload):
            self.assertIsNone(self.service._fetch_google_route("-74.08,4.65;-74.1,4.7"))

    def test_osrm_route_no_routes_returns_none(self):
        with mock.patch("geo.infrastructure.routing._fetch_json", return_value={"code": "Ok", "routes": []}):
            self.assertIsNone(self.service._fetch_osrm_route("0,0;1,1"))

    def test_valhalla_route_merges_consecutive_legs_without_duplicating_shared_point(self):
        payload = {
            "trip": {
                "status": 0,
                "legs": [
                    {"shape": POLYLINE6_FIXTURE, "summary": {"time": 10, "length": 1}},
                    {"shape": POLYLINE6_FIXTURE_CONTINUATION, "summary": {"time": 20, "length": 2}},
                ],
            }
        }
        with mock.patch("geo.infrastructure.routing._fetch_json", return_value=payload):
            route = self.service._fetch_valhalla_route("-74.08,4.65;-74.1,4.7")
        self.assertIsNotNone(route)
        # El primer tramo decodifica a 3 puntos y el segundo a 2, pero el
        # primer punto del segundo coincide con el ultimo del primero, asi
        # que se deduplican (3 + 2 - 1 = 4) en vez de sumar 5.
        self.assertEqual(len(route["geometry"]), 4)

    def test_valhalla_route_empty_shapes_returns_none(self):
        payload = {
            "trip": {
                "status": 0,
                "legs": [{"shape": "", "summary": {"time": 1, "length": 1}}],
            }
        }
        with mock.patch("geo.infrastructure.routing._fetch_json", return_value=payload):
            self.assertIsNone(self.service._fetch_valhalla_route("-74.08,4.65;-74.1,4.7"))

    def test_decode_polyline5_matches_expected_points(self):
        self.assertEqual(
            _decode_polyline5(POLYLINE5_FIXTURE),
            [[-74.08, 4.65], [-74.09, 4.66], [-74.1, 4.7]],
        )

    def test_decode_polyline6_matches_expected_points(self):
        self.assertEqual(
            _decode_polyline6(POLYLINE6_FIXTURE),
            [[-74.08, 4.65], [-74.09, 4.66], [-74.1, 4.7]],
        )


class GeoAPITests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.user = User(username="geo_user@example.com", email="geo_user@example.com", nombre="GeoUser")
        self.user.set_password("secret12345")
        self.user.save()
        access = str(RefreshToken.for_user(self.user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    @mock.patch("geo.domain.services.GeocodingService.geocode_address")
    def test_geocode_endpoint_success(self, geocode_address):
        geocode_address.return_value = GeocodedLocation(
            latitud=Decimal("4.65"), longitud=Decimal("-74.08"), direccion_texto="Calle 10, Bogota"
        )
        response = self.client.get("/api/geocode", {"direccion_texto": "Calle 10"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["direccion_texto"], "Calle 10, Bogota")

    def test_geocode_endpoint_requires_address(self):
        response = self.client.get("/api/geocode", {})
        self.assertEqual(response.status_code, 400)

    @mock.patch("geo.domain.services.GeocodingService.geocode_address")
    def test_geocode_endpoint_translates_domain_error(self, geocode_address):
        geocode_address.side_effect = ValidationError("No se pudo ubicar la dirección proporcionada")
        response = self.client.get("/api/geocode", {"direccion_texto": "xyz"})
        self.assertEqual(response.status_code, 400)

    @mock.patch("geo.domain.services.GeocodingService.suggest_addresses")
    def test_geocode_suggest_endpoint_success(self, suggest_addresses):
        suggest_addresses.return_value = [
            {"display_name": "X", "primary": "X", "secondary": "", "latitud": 4.6, "longitud": -74.1}
        ]
        response = self.client.get("/api/geocode/suggest", {"q": "rest"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["items"]), 1)

    def test_geocode_suggest_endpoint_requires_q(self):
        response = self.client.get("/api/geocode/suggest", {})
        self.assertEqual(response.status_code, 400)

    @mock.patch("geo.domain.services.GeocodingService.suggest_addresses")
    def test_geocode_suggest_endpoint_translates_domain_error(self, suggest_addresses):
        suggest_addresses.side_effect = ValidationError("La dirección es requerida")
        response = self.client.get("/api/geocode/suggest", {"q": "algo"})
        self.assertEqual(response.status_code, 400)

    @mock.patch("geo.domain.services.GeocodingService.reverse_geocode")
    def test_reverse_geocode_endpoint_success(self, reverse_geocode):
        reverse_geocode.return_value = GeocodedLocation(
            latitud=Decimal("4.65"), longitud=Decimal("-74.08"), direccion_texto="Calle 10, Bogota"
        )
        response = self.client.get("/api/geocode/reverse", {"latitud": 4.65, "longitud": -74.08})
        self.assertEqual(response.status_code, 200)

    def test_reverse_geocode_endpoint_requires_valid_bounds(self):
        response = self.client.get("/api/geocode/reverse", {"latitud": 200, "longitud": 0})
        self.assertEqual(response.status_code, 400)

    @mock.patch("geo.domain.services.GeocodingService.reverse_geocode")
    def test_reverse_geocode_endpoint_translates_domain_error(self, reverse_geocode):
        reverse_geocode.side_effect = ValidationError("No se pudo determinar la dirección de esa ubicación")
        response = self.client.get("/api/geocode/reverse", {"latitud": 4.65, "longitud": -74.08})
        self.assertEqual(response.status_code, 400)

    def test_route_endpoint_requires_authentication(self):
        anon_client = APIClient()
        response = anon_client.get("/api/route", {"coords": "-74.08,4.65;-74.1,4.7"})
        self.assertEqual(response.status_code, 401)

    @mock.patch("geo.infrastructure.routing.RouteService.get_route")
    def test_route_endpoint_success(self, get_route):
        get_route.return_value = {
            "duration": 100.0, "distance": 200.0, "geometry": [[0, 0]],
            "legs": [{"duration": 100.0, "distance": 200.0}],
        }
        response = self.client.get("/api/route", {"coords": "-74.08,4.65;-74.1,4.7"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["distance"], 200.0)

    @mock.patch("geo.infrastructure.routing.RouteService.get_route")
    def test_route_endpoint_returns_502_when_no_route_found(self, get_route):
        get_route.return_value = None
        response = self.client.get("/api/route", {"coords": "-74.08,4.65;-74.1,4.7"})
        self.assertEqual(response.status_code, 502)

    def test_route_endpoint_requires_coords(self):
        response = self.client.get("/api/route", {})
        self.assertEqual(response.status_code, 400)
