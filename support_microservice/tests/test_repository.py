import pytest

from app.repositories.support_repository import PostgresSupportRepository

from .conftest import TEST_SCHEMA, _test_dsn


@pytest.fixture
def repo():
    dsn = _test_dsn()
    repository = PostgresSupportRepository(dsn, schema=TEST_SCHEMA)
    repository.initialize()

    import psycopg

    with psycopg.connect(dsn) as connection:
        connection.execute(f'TRUNCATE TABLE "{TEST_SCHEMA}".ratings RESTART IDENTITY')
        connection.execute(f'TRUNCATE TABLE "{TEST_SCHEMA}".certificates RESTART IDENTITY')
        connection.execute(f'TRUNCATE TABLE "{TEST_SCHEMA}".transactions RESTART IDENTITY')
        connection.commit()

    return repository


def test_create_and_get_rating(repo):
    rating = repo.create_rating(usuario_id=1, autor_id=2, puntuacion=5, comentario="Excelente")
    fetched = repo.get_rating(rating.id)
    assert fetched is not None
    assert fetched.puntuacion == 5


def test_get_rating_not_found_returns_none(repo):
    assert repo.get_rating(999999) is None


def test_list_ratings_for_user_only_own_and_ordered(repo):
    repo.create_rating(usuario_id=1, autor_id=2, puntuacion=5, comentario="A")
    repo.create_rating(usuario_id=2, autor_id=3, puntuacion=4, comentario="Ajena")
    second = repo.create_rating(usuario_id=1, autor_id=2, puntuacion=3, comentario="B")

    items = repo.list_ratings_for_user(usuario_id=1)

    assert len(items) == 2
    assert items[0].id == second.id


def test_upsert_certificate_creates_then_updates(repo):
    created = repo.upsert_certificate(
        usuario_id=1, archivo_url="url1", fecha_emision="2026-01-01", estado_verificacion=False
    )
    assert created.estado_verificacion is False

    updated = repo.upsert_certificate(
        usuario_id=1, archivo_url="url2", fecha_emision="2026-02-01", estado_verificacion=True
    )
    assert updated.id == created.id
    assert updated.archivo_url == "url2"
    assert updated.estado_verificacion is True


def test_get_certificate_by_user_not_found_returns_none(repo):
    assert repo.get_certificate_by_user(999999) is None


def test_upsert_transaction_creates_then_updates(repo):
    created = repo.upsert_transaction(
        pedido_id=1, fecha_cierre=None, estado="ABIERTA", distancia_validacion_metros=0.0
    )
    assert created.estado == "ABIERTA"

    updated = repo.upsert_transaction(
        pedido_id=1, fecha_cierre="2026-01-01T00:00:00", estado="CERRADA", distancia_validacion_metros=15.5
    )
    assert updated.id == created.id
    assert updated.estado == "CERRADA"
    assert updated.fecha_cierre == "2026-01-01T00:00:00"
    assert updated.distancia_validacion_metros == 15.5


def test_get_transaction_by_order_not_found_returns_none(repo):
    assert repo.get_transaction_by_order(999999) is None


def test_initialize_is_idempotent(repo):
    repo.initialize()
    rating = repo.create_rating(usuario_id=1, autor_id=2, puntuacion=5, comentario="A")
    assert repo.get_rating(rating.id) is not None
