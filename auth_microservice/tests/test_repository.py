import psycopg
import pytest

from app.repositories.auth_repository import PostgresAuthRepository

from .conftest import TEST_SCHEMA, _test_dsn


@pytest.fixture
def repo():
    dsn = _test_dsn()
    repository = PostgresAuthRepository(dsn, schema=TEST_SCHEMA)
    repository.initialize()

    with psycopg.connect(dsn) as connection:
        connection.execute(f'TRUNCATE TABLE "{TEST_SCHEMA}".users RESTART IDENTITY')
        connection.commit()

    return repository


def test_create_and_get_user_by_id(repo):
    user = repo.create_user(username="ana", email="ana@example.com", password_hash="hash")
    fetched = repo.get_user_by_id(user.id)
    assert fetched is not None
    assert fetched.username == "ana"
    assert fetched.email == "ana@example.com"
    assert fetched.is_active is True


def test_get_user_by_id_not_found_returns_none(repo):
    assert repo.get_user_by_id(999999) is None


def test_get_user_by_email_is_case_insensitive(repo):
    repo.create_user(username="bea", email="Bea@Example.com", password_hash="hash")
    assert repo.get_user_by_email("bea@example.com") is not None
    assert repo.get_user_by_email("no-existe@example.com") is None


def test_get_user_by_username_is_case_insensitive(repo):
    repo.create_user(username="Carlos", email="carlos@example.com", password_hash="hash")
    assert repo.get_user_by_username("carlos") is not None
    assert repo.get_user_by_username("no-existe") is None


def test_initialize_is_idempotent(repo):
    # Llamar initialize() de nuevo sobre un schema ya inicializado no debe fallar.
    repo.initialize()
    user = repo.create_user(username="dora", email="dora@example.com", password_hash="hash")
    assert repo.get_user_by_id(user.id) is not None


def test_create_user_duplicate_email_raises(repo):
    repo.create_user(username="elena", email="elena@example.com", password_hash="hash")
    with pytest.raises(psycopg.errors.UniqueViolation):
        repo.create_user(username="elena2", email="elena@example.com", password_hash="hash")
