from __future__ import annotations

from app.geocoding_service import GeocodingService


def test_poi_fallback_matches_hits_and_misses():
    assert GeocodingService._poi_fallback_matches("cerca de la eafit") != []
    assert GeocodingService._poi_fallback_matches("") == []
    assert GeocodingService._poi_fallback_matches("algo random sin poi") == []


def test_poi_fallback_location_returns_first_hit():
    loc = GeocodingService._poi_fallback_location("Universidad EAFIT")
    assert loc is not None
    assert "EAFIT" in loc.direccion_texto

    assert GeocodingService()._poi_fallback_location("direccion cualquiera") is None


def test_split_display_name():
    assert GeocodingService._split_display_name("") == ("", "")
    assert GeocodingService._split_display_name("Solo") == ("Solo", "")
    assert GeocodingService._split_display_name("Calle 1, Medellin, Antioquia") == (
        "Calle 1",
        "Medellin, Antioquia",
    )


def test_split_suggestion_display_prefers_name_field():
    service = GeocodingService()
    item = {
        "display_name": "Universidad EAFIT, Cra 49, El Poblado",
        "address": {"name": "Universidad EAFIT", "road": "Cra 49", "city": "Medellin"},
    }
    primary, secondary = service._split_suggestion_display(item)
    assert primary == "Universidad EAFIT"
    assert "Medellin" in secondary


def test_split_suggestion_display_falls_back_to_road_and_house():
    service = GeocodingService()
    # display_name debe coincidir exactamente con 'road' (sin numero) para que
    # se use la rama road+house en vez de la rama display_primary.
    item = {
        "display_name": "Cra 49, El Poblado",
        "address": {"road": "Cra 49", "house_number": "10", "city": "Medellin"},
    }
    primary, _ = service._split_suggestion_display(item)
    assert primary == "Cra 49 10"


def test_split_suggestion_display_without_address_dict():
    service = GeocodingService()
    item = {"display_name": "Solo display, Segundo"}
    assert service._split_suggestion_display(item) == ("Solo display", "Segundo")


def test_is_within_medellin_viewbox_handles_bad_config(monkeypatch):
    monkeypatch.setattr(GeocodingService, "MEDELLIN_VIEWBOX", "not-a-viewbox", raising=False)
    assert GeocodingService._is_within_medellin_viewbox(6.2, -75.5) is False


def test_looks_like_medellin_result_by_text():
    item = {"display_name": "Algo, Medellin, Antioquia, Colombia"}
    assert GeocodingService._looks_like_medellin_result(item) is True


def test_looks_like_medellin_result_by_address_fields():
    item = {"display_name": "Algo", "address": {"city": "Medellin", "state": "Antioquia"}}
    assert GeocodingService._looks_like_medellin_result(item) is True


def test_looks_like_medellin_result_false_for_other_department():
    item = {"display_name": "Algo, Cali, Valle del Cauca"}
    assert GeocodingService._looks_like_medellin_result(item) is False


def test_looks_like_medellin_result_false_when_address_not_dict():
    item = {"display_name": "Algo sin antioquia", "address": "no-dict"}
    assert GeocodingService._looks_like_medellin_result(item) is False


def test_looks_like_place_query():
    assert GeocodingService._looks_like_place_query("Universidad EAFIT") is True
    assert GeocodingService._looks_like_place_query("") is False
    assert GeocodingService._looks_like_place_query("Calle 5 #80-10") is False
    assert GeocodingService._looks_like_place_query("123") is False


def test_strip_place_noise():
    assert GeocodingService._strip_place_noise("Parque Lleras") == "lleras"
    assert GeocodingService._strip_place_noise("Centro Comercial Santafe") == "santafe"
    assert GeocodingService._strip_place_noise("") == ""
    assert GeocodingService._strip_place_noise("Sin prefijo reconocido") == ""


def test_normalize_co_address_query_expands_abbreviations():
    assert GeocodingService._normalize_co_address_query("cl 10").startswith("Calle 10")
    assert GeocodingService._normalize_co_address_query("cra 43a").startswith("Carrera 43a")
    assert GeocodingService._normalize_co_address_query("") == ""


def test_normalize_co_address_query_rebuilds_hash_format():
    result = GeocodingService._normalize_co_address_query("Calle 5 #80c125")
    assert result == "Calle 5 #80C-125"


def test_normalize_co_address_query_rebuilds_no_hash_format():
    result = GeocodingService._normalize_co_address_query("Calle 5 80c125")
    assert result == "Calle 5 #80C-125"


def test_looks_like_co_street_query():
    assert GeocodingService._looks_like_co_street_query("Calle 5 #80-10") is True
    assert GeocodingService._looks_like_co_street_query("cra 43 con 10") is True
    assert GeocodingService._looks_like_co_street_query("") is False
    assert GeocodingService._looks_like_co_street_query("Universidad EAFIT") is False


def test_contains_other_colombian_city_hint():
    # Metodo sin llamadores en el codigo actual (dead code); se documenta el
    # comportamiento real: \bbogot\b requiere una frontera de palabra justo
    # tras "bogot", por lo que "Bogota" (palabra completa) NO matchea, solo
    # apariciones literales del prefijo "bogot" seguido de un separador.
    assert GeocodingService._contains_other_colombian_city_hint("algo en bogot medellin") is True
    assert GeocodingService._contains_other_colombian_city_hint("algo en Bogota") is False
    assert GeocodingService._contains_other_colombian_city_hint("algo en cali") is True
    assert GeocodingService._contains_other_colombian_city_hint("algo en Medellin") is False


def test_detect_query_scope():
    assert GeocodingService._detect_query_scope("") == "global"
    assert GeocodingService._detect_query_scope("Medellin centro") == "colombia"
    assert GeocodingService._detect_query_scope("Antioquia rural") == "colombia"
    assert GeocodingService._detect_query_scope("Calle 5 #80-10") == "colombia"
    assert GeocodingService._detect_query_scope("Paris France") == "global"


def test_add_default_context_if_needed():
    assert GeocodingService._add_default_context_if_needed("", scope="colombia") == ""
    assert GeocodingService._add_default_context_if_needed("Calle 5", scope="colombia") == "Calle 5, Colombia"
    assert (
        GeocodingService._add_default_context_if_needed("Calle 5, Colombia", scope="colombia")
        == "Calle 5, Colombia"
    )
    assert GeocodingService._add_default_context_if_needed("Paris", scope="global") == "Paris"


def test_generalize_co_house_number_variant():
    assert GeocodingService._generalize_co_house_number_variant("") == ""
    assert GeocodingService._generalize_co_house_number_variant("Calle 5 #80C-125") == "Calle 5 #80C"
    assert GeocodingService._generalize_co_house_number_variant("Calle 5 80C") == "Calle 5 #80C"
    assert GeocodingService._generalize_co_house_number_variant("texto sin match") == ""


def test_road_only_variant():
    assert GeocodingService._road_only_variant("") == ""
    assert GeocodingService._road_only_variant("Calle 5 #80C-125") == "Calle 5"
    assert GeocodingService._road_only_variant("Calle 5 #80C-125, Medellin") == "Calle 5, Medellin"
    assert GeocodingService._road_only_variant("texto sin via reconocible") == ""


def test_co_address_display_prefix():
    assert GeocodingService._co_address_display_prefix("") == ""
    assert GeocodingService._co_address_display_prefix("Calle 5 #80-10, Medellin") == "Calle 5 #80-10"


def test_fallback_queries_for_co():
    assert GeocodingService._fallback_queries_for_co("") == []
    variants = GeocodingService._fallback_queries_for_co("Calle 5 #80C-125")
    assert "Calle 5 #80C" in variants
    # No debe repetir la direccion original ni duplicados.
    assert "Calle 5 #80C-125" not in variants


def test_geocode_cache_roundtrip_and_expiry(monkeypatch):
    from app.geocoding_service import GeocodedLocation
    from decimal import Decimal

    loc = GeocodedLocation(latitud=Decimal("6.2"), longitud=Decimal("-75.5"), direccion_texto="X")
    GeocodingService._geocode_cache_set("mi direccion", loc)
    assert GeocodingService._geocode_cache_get("MI DIRECCION") is loc

    # Forzar expiracion retrocediendo el timestamp guardado.
    key = "mi direccion"
    ts, cached = GeocodingService._geocode_cache[key]
    GeocodingService._geocode_cache[key] = (ts - 10_000, cached)
    assert GeocodingService._geocode_cache_get("mi direccion") is None


def test_geocode_cache_evicts_oldest_when_full(monkeypatch):
    from app.geocoding_service import GeocodedLocation
    from decimal import Decimal

    monkeypatch.setattr(GeocodingService, "_GEOCODE_CACHE_MAX", 1)
    loc = GeocodedLocation(latitud=Decimal("1"), longitud=Decimal("1"), direccion_texto="A")
    GeocodingService._geocode_cache_set("primero", loc)
    GeocodingService._geocode_cache_set("segundo", loc)
    assert "primero" not in GeocodingService._geocode_cache
    assert "segundo" in GeocodingService._geocode_cache


def test_suggest_cache_roundtrip_and_expiry():
    GeocodingService._suggest_cache_set("query", 5, [{"a": 1}])
    assert GeocodingService._suggest_cache_get("QUERY", 5) == [{"a": 1}]

    key = ("query", 5)
    ts, items = GeocodingService._suggest_cache[key]
    GeocodingService._suggest_cache[key] = (ts - 10_000, items)
    assert GeocodingService._suggest_cache_get("query", 5) is None


def test_suggest_cache_negative_result_expires_faster():
    GeocodingService._suggest_cache_set("sin resultados", 5, [])
    key = ("sin resultados", 5)
    ts, items = GeocodingService._suggest_cache[key]
    # Un timestamp de hace 10s ya vence el TTL negativo (5s) pero no el positivo (120s).
    GeocodingService._suggest_cache[key] = (ts - 10, items)
    assert GeocodingService._suggest_cache_get("sin resultados", 5) is None


def test_suggest_cache_evicts_oldest_when_full(monkeypatch):
    monkeypatch.setattr(GeocodingService, "_SUGGEST_CACHE_MAX", 1)
    GeocodingService._suggest_cache_set("primero", 5, [{"a": 1}])
    GeocodingService._suggest_cache_set("segundo", 5, [{"a": 1}])
    assert ("primero", 5) not in GeocodingService._suggest_cache
    assert ("segundo", 5) in GeocodingService._suggest_cache
