import sqlite3

import pytest

from app.repositories.market_repository import SQLiteMarketRepository


@pytest.fixture
def repo(tmp_path):
    repository = SQLiteMarketRepository(str(tmp_path / "market.db"))
    repository.initialize()
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


def test_create_publication_uses_shared_schema_columns_when_present(tmp_path):
    """Si la tabla ya tiene columnas del monolito (usuario_id, categoria,
    ingredientes, estado, created_at), create_publication debe rellenarlas."""
    db_path = tmp_path / "shared.db"
    repository = SQLiteMarketRepository(str(db_path))
    repository.initialize()

    with sqlite3.connect(db_path) as connection:
        connection.execute("ALTER TABLE publications ADD COLUMN usuario_id INTEGER")
        connection.execute("ALTER TABLE publications ADD COLUMN categoria TEXT")
        connection.execute("ALTER TABLE publications ADD COLUMN ingredientes TEXT")
        connection.execute("ALTER TABLE publications ADD COLUMN estado TEXT")
        connection.execute("ALTER TABLE publications ADD COLUMN created_at TEXT")
        connection.commit()

    pub = repository.create_publication(
        autor_id=7, titulo="X", descripcion="Y", precio=1.0, direccion_texto="Z"
    )

    with sqlite3.connect(db_path) as connection:
        row = connection.execute(
            "SELECT usuario_id, categoria, estado FROM publications WHERE id = ?", (pub.id,)
        ).fetchone()
    assert row[0] == 7
    assert row[1] == ""
    assert row[2] == "ACTIVA"


def test_create_order_uses_shared_schema_columns_when_present(tmp_path):
    """Si la tabla ya tiene columnas del monolito (usuario_id, telefono,
    direccion_entrega, created_at), create_order debe rellenarlas."""
    db_path = tmp_path / "shared_orders.db"
    repository = SQLiteMarketRepository(str(db_path))
    repository.initialize()

    with sqlite3.connect(db_path) as connection:
        connection.execute("ALTER TABLE orders ADD COLUMN usuario_id INTEGER")
        connection.execute("ALTER TABLE orders ADD COLUMN telefono TEXT")
        connection.execute("ALTER TABLE orders ADD COLUMN direccion_entrega TEXT")
        connection.execute("ALTER TABLE orders ADD COLUMN created_at TEXT")
        connection.commit()

    pub = repository.create_publication(
        autor_id=1, titulo="X", descripcion="Y", precio=1.0, direccion_texto="Z"
    )
    order = repository.create_order(
        publicacion_id=pub.id, comprador_id=9, cantidad=2, total=2.0, estado="pendiente"
    )

    with sqlite3.connect(db_path) as connection:
        row = connection.execute(
            "SELECT usuario_id, telefono, direccion_entrega FROM orders WHERE id = ?", (order.id,)
        ).fetchone()
    assert row[0] == 9
    assert row[1] == ""
    assert row[2] == ""


def test_schema_compatibility_backfills_legacy_publications_table(tmp_path):
    """Una tabla vieja (sin autor_id/direccion_texto/disponibilidad) debe
    quedar migrada tras initialize() sin perder las filas existentes."""
    db_path = tmp_path / "legacy_pub.db"
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE publications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                titulo TEXT NOT NULL,
                descripcion TEXT NOT NULL,
                precio REAL NOT NULL
            )
            """
        )
        connection.execute("INSERT INTO publications (titulo, descripcion, precio) VALUES ('Legacy', 'x', 5.0)")
        connection.commit()

    repository = SQLiteMarketRepository(str(db_path))
    repository.initialize()

    items = repository.list_publications()
    assert len(items) == 1
    assert items[0].autor_id == 0
    assert items[0].disponibilidad is True
    assert items[0].direccion_texto == ""


def test_schema_compatibility_backfills_legacy_orders_table(tmp_path):
    """Una tabla vieja de orders (sin comprador_id/cantidad/total/estado)
    debe quedar migrada tras initialize()."""
    db_path = tmp_path / "legacy_orders.db"
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE publications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                autor_id INTEGER NOT NULL,
                titulo TEXT NOT NULL,
                descripcion TEXT NOT NULL,
                precio REAL NOT NULL,
                disponibilidad INTEGER NOT NULL DEFAULT 1,
                direccion_texto TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                publicacion_id INTEGER NOT NULL
            )
            """
        )
        connection.execute(
            "INSERT INTO publications (autor_id, titulo, descripcion, precio, direccion_texto) "
            "VALUES (1, 'A', 'x', 1.0, 'Calle 1')"
        )
        connection.execute("INSERT INTO orders (publicacion_id) VALUES (1)")
        connection.commit()

    repository = SQLiteMarketRepository(str(db_path))
    repository.initialize()

    items = repository.list_orders()
    assert len(items) == 1
    assert items[0].comprador_id == 0
    assert items[0].cantidad == 1
    assert items[0].total == 0
    assert items[0].estado == "pendiente"
