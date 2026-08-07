from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from decimal import Decimal
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from common.exceptions import ValidationError


@dataclass
class GeocodedLocation:
    latitud: Decimal
    longitud: Decimal
    direccion_texto: str


class GeocodingService:
    """Geocodificacion de direcciones via Google Maps Platform (Geocoding API
    + Places API). Requiere GOOGLE_MAPS_API_KEY configurada en el entorno."""

    _REGION_BIAS = "co"

    _GEOCODE_CACHE_TTL_SECONDS = 600
    _SUGGEST_CACHE_TTL_SECONDS = 120
    _GEOCODE_CACHE_MAX = 500
    _SUGGEST_CACHE_MAX = 300
    _geocode_cache: dict[str, tuple[float, GeocodedLocation]] = {}
    _suggest_cache: dict[tuple, tuple[float, list[dict]]] = {}

    def geocode_address(self, *, direccion_texto: str) -> GeocodedLocation:
        direccion = (direccion_texto or "").strip()
        if not direccion:
            raise ValidationError("La dirección es requerida")

        cached = self._geocode_cache_get(direccion)
        if cached is not None:
            return cached

        result = self._google_geocode(direccion)
        if result is None:
            raise ValidationError("No se pudo ubicar la dirección proporcionada")

        self._geocode_cache_set(direccion, result)
        return result

    def suggest_addresses(self, *, query: str, limit: int = 5) -> list[dict]:
        q = (query or "").strip()
        if not q:
            raise ValidationError("La dirección es requerida")

        safe_limit = max(1, min(int(limit or 5), 10))
        cache_key = (q.lower(), safe_limit)

        cached = self._suggest_cache_get(cache_key)
        if cached is not None:
            return cached

        items = self._google_text_search(q, limit=safe_limit)
        self._suggest_cache_set(cache_key, items)
        return items

    # --- Google Maps Platform ---

    @staticmethod
    def _api_key() -> str:
        key = os.environ.get("GOOGLE_MAPS_API_KEY", "").strip()
        if not key:
            raise ValidationError("GOOGLE_MAPS_API_KEY no está configurada")
        return key

    def _google_geocode(self, direccion_texto: str) -> GeocodedLocation | None:
        params = urlencode(
            {
                "address": direccion_texto,
                "region": self._REGION_BIAS,
                "key": self._api_key(),
            }
        )
        data = self._fetch_json(f"https://maps.googleapis.com/maps/api/geocode/json?{params}")
        if not data or data.get("status") != "OK":
            return None

        results = data.get("results") or []
        if not results:
            return None

        top = results[0]
        location = (top.get("geometry") or {}).get("location") or {}
        lat = location.get("lat")
        lng = location.get("lng")
        if lat is None or lng is None:
            return None

        return GeocodedLocation(
            latitud=Decimal(str(lat)),
            longitud=Decimal(str(lng)),
            direccion_texto=top.get("formatted_address") or direccion_texto,
        )

    def _google_text_search(self, query: str, *, limit: int) -> list[dict]:
        params = urlencode(
            {
                "query": query,
                "region": self._REGION_BIAS,
                "key": self._api_key(),
            }
        )
        data = self._fetch_json(f"https://maps.googleapis.com/maps/api/place/textsearch/json?{params}")
        if not data or data.get("status") not in {"OK", "ZERO_RESULTS"}:
            return []

        items: list[dict] = []
        for result in (data.get("results") or [])[:limit]:
            location = (result.get("geometry") or {}).get("location") or {}
            lat = location.get("lat")
            lng = location.get("lng")
            if lat is None or lng is None:
                continue

            primary = result.get("name") or result.get("formatted_address") or query
            secondary = result.get("formatted_address") or ""
            items.append(
                {
                    "display_name": result.get("formatted_address") or primary,
                    "primary": primary,
                    "secondary": secondary,
                    "latitud": float(lat),
                    "longitud": float(lng),
                }
            )

        return items

    @staticmethod
    def _fetch_json(url: str):
        try:
            req = Request(url, headers={"Accept": "application/json"})
            with urlopen(req, timeout=6) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception:
            return None

    # --- Cache en memoria (reduce llamadas facturables a Google) ---

    @classmethod
    def _geocode_cache_get(cls, key: str) -> GeocodedLocation | None:
        entry = cls._geocode_cache.get(key.lower())
        if not entry:
            return None
        expires_at, value = entry
        if time.time() > expires_at:
            cls._geocode_cache.pop(key.lower(), None)
            return None
        return value

    @classmethod
    def _geocode_cache_set(cls, key: str, value: GeocodedLocation) -> None:
        if len(cls._geocode_cache) >= cls._GEOCODE_CACHE_MAX:
            cls._geocode_cache.clear()
        cls._geocode_cache[key.lower()] = (time.time() + cls._GEOCODE_CACHE_TTL_SECONDS, value)

    @classmethod
    def _suggest_cache_get(cls, key: tuple) -> list[dict] | None:
        entry = cls._suggest_cache.get(key)
        if not entry:
            return None
        expires_at, value = entry
        if time.time() > expires_at:
            cls._suggest_cache.pop(key, None)
            return None
        return value

    @classmethod
    def _suggest_cache_set(cls, key: tuple, value: list[dict]) -> None:
        if len(cls._suggest_cache) >= cls._SUGGEST_CACHE_MAX:
            cls._suggest_cache.clear()
        cls._suggest_cache[key] = (time.time() + cls._SUGGEST_CACHE_TTL_SECONDS, value)
