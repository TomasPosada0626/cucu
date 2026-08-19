import pytest

from app.repositories.notification_repository import PostgresNotificationRepository

from .conftest import TEST_SCHEMA, _test_dsn, _truncate


@pytest.fixture
def repo():
    repository = PostgresNotificationRepository(_test_dsn(), schema=TEST_SCHEMA)
    repository.initialize()
    _truncate()
    return repository


def test_create_and_get_by_id(repo):
    notif = repo.create(usuario_id=1, tipo="pedido", mensaje="Hola")
    fetched = repo.get_by_id(notif.id)
    assert fetched is not None
    assert fetched.mensaje == "Hola"
    assert fetched.leida is False


def test_get_by_id_not_found_returns_none(repo):
    assert repo.get_by_id(999999) is None


def test_list_by_user_only_returns_own_and_ordered(repo):
    repo.create(usuario_id=1, tipo="pedido", mensaje="Mia1")
    repo.create(usuario_id=2, tipo="pedido", mensaje="Ajena")
    second = repo.create(usuario_id=1, tipo="pedido", mensaje="Mia2")

    items = repo.list_by_user(usuario_id=1)

    assert len(items) == 2
    assert items[0].id == second.id


def test_mark_as_read(repo):
    notif = repo.create(usuario_id=1, tipo="pedido", mensaje="Hola")
    updated = repo.mark_as_read(notif.id)
    assert updated.leida is True


def test_mark_as_read_nonexistent_returns_none(repo):
    assert repo.mark_as_read(999999) is None


def test_register_processed_event_is_idempotent(repo):
    assert repo.register_processed_event(event_id="evt-1") is True
    assert repo.register_processed_event(event_id="evt-1") is False


def test_initialize_is_idempotent(repo):
    repo.initialize()
    notif = repo.create(usuario_id=1, tipo="pedido", mensaje="Hola")
    assert repo.get_by_id(notif.id) is not None
