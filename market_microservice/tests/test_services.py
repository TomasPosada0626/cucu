from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.errors import NotFoundError, ValidationError
from app.services import MarketService


@pytest.fixture
def repo():
    return MagicMock()


@pytest.fixture
def service(repo):
    return MarketService(repository=repo)


def test_create_publication_rejects_invalid_autor_id(service):
    with pytest.raises(ValidationError):
        service.create_publication(autor_id=0, titulo="X", descripcion="Y", precio=1, direccion_texto="Z")


def test_create_publication_rejects_blank_titulo(service):
    with pytest.raises(ValidationError):
        service.create_publication(autor_id=1, titulo="   ", descripcion="Y", precio=1, direccion_texto="Z")


def test_create_publication_rejects_blank_descripcion(service):
    with pytest.raises(ValidationError):
        service.create_publication(autor_id=1, titulo="X", descripcion="  ", precio=1, direccion_texto="Z")


def test_create_publication_rejects_blank_direccion(service):
    with pytest.raises(ValidationError):
        service.create_publication(autor_id=1, titulo="X", descripcion="Y", precio=1, direccion_texto="  ")


def test_create_publication_rejects_non_numeric_precio(service):
    with pytest.raises(ValidationError):
        service.create_publication(autor_id=1, titulo="X", descripcion="Y", precio="abc", direccion_texto="Z")


def test_create_publication_rejects_non_positive_precio(service):
    with pytest.raises(ValidationError):
        service.create_publication(autor_id=1, titulo="X", descripcion="Y", precio=0, direccion_texto="Z")


def test_create_publication_success_delegates_to_repo(service, repo):
    repo.create_publication.return_value = "created"
    result = service.create_publication(
        autor_id=1, titulo=" X ", descripcion=" Y ", precio="10.5", direccion_texto=" Z "
    )
    assert result == "created"
    repo.create_publication.assert_called_once_with(
        autor_id=1, titulo="X", descripcion="Y", precio=10.5, direccion_texto="Z"
    )


def test_list_publications_delegates_to_repo(service, repo):
    repo.list_publications.return_value = ["a"]
    assert service.list_publications() == ["a"]


def test_create_order_rejects_non_numeric_ids(service):
    with pytest.raises(ValidationError):
        service.create_order(publicacion_id="abc", comprador_id=1, cantidad=1)


def test_create_order_rejects_non_positive_ids(service):
    with pytest.raises(ValidationError):
        service.create_order(publicacion_id=0, comprador_id=1, cantidad=1)


def test_create_order_rejects_non_positive_cantidad(service):
    with pytest.raises(ValidationError):
        service.create_order(publicacion_id=1, comprador_id=1, cantidad=0)


def test_create_order_publication_not_found_raises(service, repo):
    repo.get_publication.return_value = None
    with pytest.raises(NotFoundError):
        service.create_order(publicacion_id=1, comprador_id=1, cantidad=1)


def test_create_order_success_computes_total(service, repo):
    publication = MagicMock(precio=10.0)
    repo.get_publication.return_value = publication
    repo.create_order.return_value = "order"

    result = service.create_order(publicacion_id=1, comprador_id=2, cantidad=3)

    assert result == "order"
    repo.create_order.assert_called_once_with(
        publicacion_id=1, comprador_id=2, cantidad=3, total=30.0, estado="pendiente"
    )


def test_list_orders_delegates_to_repo(service, repo):
    repo.list_orders.return_value = ["o"]
    assert service.list_orders() == ["o"]


def test_get_order_not_found_raises(service, repo):
    repo.get_order.return_value = None
    with pytest.raises(NotFoundError):
        service.get_order(order_id=1)


def test_get_order_success(service, repo):
    repo.get_order.return_value = "order"
    assert service.get_order(order_id=1) == "order"
