from __future__ import annotations

from ...domain.services import CatalogService
from ...infrastructure.cache import invalidate_catalog_cache


class ListPublicacionesUseCase:
    def __init__(self, *, catalog_service: CatalogService | None = None):
        self._catalog_service = catalog_service or CatalogService()

    def execute(self):
        return self._catalog_service.list_publicaciones()


class ListPublicacionesCercanasUseCase:
    def __init__(self, *, catalog_service: CatalogService | None = None):
        self._catalog_service = catalog_service or CatalogService()

    def execute(self, **filters):
        return self._catalog_service.list_publicaciones_cercanas(**filters)


class CreatePublicacionUseCase:
    def __init__(self, *, catalog_service: CatalogService | None = None):
        self._catalog_service = catalog_service or CatalogService()

    def execute(self, *, user, **payload):
        publicacion = self._catalog_service.create_publicacion(user=user, **payload)
        invalidate_catalog_cache()
        return publicacion


class ListPublicacionesForUserUseCase:
    def __init__(self, *, catalog_service: CatalogService | None = None):
        self._catalog_service = catalog_service or CatalogService()

    def execute(self, *, user):
        return self._catalog_service.list_publicaciones_for_user(user=user)


class UpdatePublicacionUseCase:
    def __init__(self, *, catalog_service: CatalogService | None = None):
        self._catalog_service = catalog_service or CatalogService()

    def execute(self, *, user, publicacion_id: int, **changes):
        publicacion = self._catalog_service.update_publicacion(
            user=user,
            publicacion_id=publicacion_id,
            **changes,
        )
        invalidate_catalog_cache()
        return publicacion


class DeletePublicacionUseCase:
    def __init__(self, *, catalog_service: CatalogService | None = None):
        self._catalog_service = catalog_service or CatalogService()

    def execute(self, *, user, publicacion_id: int):
        self._catalog_service.delete_publicacion(
            user=user,
            publicacion_id=publicacion_id,
        )
        invalidate_catalog_cache()
