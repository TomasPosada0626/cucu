from __future__ import annotations

from django.core.cache import cache

CATALOG_CACHE_KEY = "market:catalog:publicaciones"
CATALOG_CACHE_TTL_SECONDS = 30


def invalidate_catalog_cache() -> None:
    cache.delete(CATALOG_CACHE_KEY)
