from __future__ import annotations

import pytest

from app.geocoding_service import GeocodingService
from app.factory import create_app


@pytest.fixture(autouse=True)
def _clear_geocoding_caches():
    GeocodingService._suggest_cache.clear()
    GeocodingService._geocode_cache.clear()
    GeocodingService._nominatim_backoff_until = 0.0
    yield
    GeocodingService._suggest_cache.clear()
    GeocodingService._geocode_cache.clear()
    GeocodingService._nominatim_backoff_until = 0.0


@pytest.fixture
def app():
    flask_app = create_app()
    flask_app.config["TESTING"] = True
    yield flask_app


@pytest.fixture
def client(app):
    return app.test_client()
