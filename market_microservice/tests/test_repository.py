import pytest

from app.repositories.market_repository import PostgresMarketRepository

from .conftest import TEST_SCHEMA, _test_dsn, _truncate


@pytest.fixture
def repo():
    repository = PostgresMarketRepository(_test_dsn(), schema=TEST_SCHEMA)
    repository.initialize()
    _truncate()
    return repository


def test_create_and_get_publication(repo):
    pub = repo.create_publication(
        autor_id=1, titulo="Sopa", descripcion="Rica", precio=10.0, direccion_texto="Calle 1"
    )
    fetched = repo.get_publication(pub.id)
    assert fetched is not None
    assert fetched.titulo == "Sopa"
    assert fetched.disponibilidad is True


def test_get_publication_not_found_returns_none(repo):
    assert repo.get_publication(999999) is None


def test_list_publications_orders_by_id_desc(repo):
    first = repo.create_publication(autor_id=1, titulo="A", descripcion="x", precio=1.0, direccion_texto="x")
    second = repo.create_publication(autor_id=1, titulo="B", descripcion="x", precio=1.0, direccion_texto="x")
    items = repo.list_publications()
    assert [i.id for i in items] == [second.id, first.id]


def test_create_and_get_order(repo):
    pub = repo.create_publication(autor_id=1, titulo="A", descripcion="x", precio=5.0, direccion_texto="x")
    order = repo.create_order(publicacion_id=pub.id, comprador_id=2, cantidad=3, total=15.0, estado="pendiente")
    fetched = repo.get_order(order.id)
    assert fetched is not None
    assert fetched.cantidad == 3
    assert fetched.total == 15.0


def test_get_order_not_found_returns_none(repo):
    assert repo.get_order(999999) is None


def test_list_orders_orders_by_id_desc(repo):
    pub = repo.create_publication(autor_id=1, titulo="A", descripcion="x", precio=1.0, direccion_texto="x")
    first = repo.create_order(publicacion_id=pub.id, comprador_id=1, cantidad=1, total=1.0, estado="pendiente")
    second = repo.create_order(publicacion_id=pub.id, comprador_id=1, cantidad=1, total=1.0, estado="pendiente")
    items = repo.list_orders()
    assert [i.id for i in items] == [second.id, first.id]


def test_initialize_is_idempotent(repo):
    repo.initialize()
    pub = repo.create_publication(autor_id=1, titulo="A", descripcion="x", precio=1.0, direccion_texto="x")
    assert repo.get_publication(pub.id) is not None
