import sqlite3

import pytest

from app.repositories.auth_repository import SQLiteAuthRepository


@pytest.fixture
def repo(tmp_path):
    repository = SQLiteAuthRepository(str(tmp_path / "auth.db"))
    repository.initialize()
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
    # Llamar initialize() de nuevo sobre una base ya inicializada no debe fallar.
    repo.initialize()
    user = repo.create_user(username="dora", email="dora@example.com", password_hash="hash")
    assert repo.get_user_by_id(user.id) is not None


def test_create_user_uses_extra_columns_when_present(tmp_path):
    """Si la tabla ya tiene columna 'fecha_registro' (compartiendo esquema con
    el monolito Django), create_user debe rellenarla tambien. La columna
    'nombre' ya la garantiza initialize() para todo esquema."""
    db_path = tmp_path / "shared.db"
    repository = SQLiteAuthRepository(str(db_path))
    repository.initialize()

    with sqlite3.connect(db_path) as connection:
        connection.execute("ALTER TABLE users ADD COLUMN fecha_registro TEXT")
        connection.commit()

    user = repository.create_user(username="elena", email="elena@example.com", password_hash="hash")

    with sqlite3.connect(db_path) as connection:
        row = connection.execute(
            "SELECT nombre, fecha_registro FROM users WHERE id = ?", (user.id,)
        ).fetchone()
    assert row[0] == "elena"
    assert row[1] is not None


def test_schema_compatibility_backfills_legacy_table(tmp_path):
    """Una tabla `users` preexistente con el esquema viejo de Django (sin
    username/password_hash/is_active) debe quedar migrada tras initialize()."""
    db_path = tmp_path / "legacy.db"
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT,
                email TEXT NOT NULL UNIQUE
            )
            """
        )
        connection.execute("INSERT INTO users (nombre, email) VALUES ('Legacy User', 'legacy@example.com')")
        connection.commit()

    repository = SQLiteAuthRepository(str(db_path))
    repository.initialize()

    user = repository.get_user_by_email("legacy@example.com")
    assert user is not None
    # El backfill genera 'user_<id>' (no copia desde 'nombre'); el id es 1
    # porque es la unica fila insertada antes de migrar el esquema.
    assert user.username == f"user_{user.id}"
    assert user.is_active is True


def test_schema_compatibility_backfills_missing_email(tmp_path):
    """Una tabla sin columna email tambien debe migrarse: se genera un email
    placeholder a partir del username para que las columnas NOT NULL/UNIQUE
    de la tabla nueva no rompan filas preexistentes."""
    db_path = tmp_path / "no_email.db"
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE
            )
            """
        )
        connection.execute("INSERT INTO users (username) VALUES ('sinemail')")
        connection.commit()

    repository = SQLiteAuthRepository(str(db_path))
    repository.initialize()

    user = repository.get_user_by_username("sinemail")
    assert user is not None
    assert user.email == "sinemail@local.invalid"
