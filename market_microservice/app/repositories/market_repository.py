from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from ..models import Order, Publication


class SQLiteMarketRepository:
    def __init__(self, database_path: str) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS publications (
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
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    publicacion_id INTEGER NOT NULL,
                    comprador_id INTEGER NOT NULL,
                    cantidad INTEGER NOT NULL,
                    total REAL NOT NULL,
                    estado TEXT NOT NULL,
                    FOREIGN KEY (publicacion_id) REFERENCES publications(id)
                )
                """
            )
            self._ensure_schema_compatibility(connection)
            connection.commit()

    def _ensure_schema_compatibility(self, connection: sqlite3.Connection) -> None:
        publication_columns = self._get_columns(connection, "publications")
        if "autor_id" not in publication_columns:
            connection.execute("ALTER TABLE publications ADD COLUMN autor_id INTEGER NOT NULL DEFAULT 0")
        if "direccion_texto" not in publication_columns:
            connection.execute("ALTER TABLE publications ADD COLUMN direccion_texto TEXT NOT NULL DEFAULT ''")
        if "disponibilidad" not in publication_columns:
            connection.execute("ALTER TABLE publications ADD COLUMN disponibilidad INTEGER NOT NULL DEFAULT 1")

        order_columns = self._get_columns(connection, "orders")
        if "comprador_id" not in order_columns:
            connection.execute("ALTER TABLE orders ADD COLUMN comprador_id INTEGER NOT NULL DEFAULT 0")
        if "cantidad" not in order_columns:
            connection.execute("ALTER TABLE orders ADD COLUMN cantidad INTEGER NOT NULL DEFAULT 1")
        if "total" not in order_columns:
            connection.execute("ALTER TABLE orders ADD COLUMN total REAL NOT NULL DEFAULT 0")
        if "estado" not in order_columns:
            connection.execute("ALTER TABLE orders ADD COLUMN estado TEXT NOT NULL DEFAULT 'pendiente'")

    @staticmethod
    def _get_columns(connection: sqlite3.Connection, table_name: str) -> set[str]:
        rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
        return {str(row[1]) for row in rows}

    def create_publication(self, *, autor_id: int, titulo: str, descripcion: str, precio: float, direccion_texto: str) -> Publication:
        with self._connect() as connection:
            columns = self._get_columns(connection, "publications")
            insert_columns: list[str] = ["titulo", "descripcion", "precio"]
            values: list[object] = [titulo, descripcion, precio]

            if "autor_id" in columns:
                insert_columns.append("autor_id")
                values.append(autor_id)
            if "usuario_id" in columns:
                insert_columns.append("usuario_id")
                values.append(autor_id)
            if "disponibilidad" in columns:
                insert_columns.append("disponibilidad")
                values.append(1)
            if "direccion_texto" in columns:
                insert_columns.append("direccion_texto")
                values.append(direccion_texto)
            if "categoria" in columns:
                insert_columns.append("categoria")
                values.append("")
            if "ingredientes" in columns:
                insert_columns.append("ingredientes")
                values.append("[]")
            if "estado" in columns:
                insert_columns.append("estado")
                values.append("ACTIVA")
            if "created_at" in columns:
                insert_columns.append("created_at")
                values.append(datetime.now(timezone.utc).isoformat())

            placeholders = ", ".join(["?"] * len(insert_columns))
            sql = f"INSERT INTO publications ({', '.join(insert_columns)}) VALUES ({placeholders})"
            cursor = connection.execute(sql, values)
            connection.commit()
            pub_id = int(cursor.lastrowid)
        publication = self.get_publication(pub_id)
        assert publication is not None
        return publication

    def list_publications(self) -> list[Publication]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, autor_id, titulo, descripcion, precio, disponibilidad, direccion_texto
                FROM publications
                ORDER BY id DESC
                """
            ).fetchall()
        return [self._map_publication(r) for r in rows]

    def get_publication(self, publication_id: int) -> Publication | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, autor_id, titulo, descripcion, precio, disponibilidad, direccion_texto
                FROM publications
                WHERE id = ?
                """,
                (publication_id,),
            ).fetchone()
        return self._map_publication(row) if row else None

    def create_order(self, *, publicacion_id: int, comprador_id: int, cantidad: int, total: float, estado: str) -> Order:
        with self._connect() as connection:
            columns = self._get_columns(connection, "orders")
            insert_columns: list[str] = ["publicacion_id", "total", "estado"]
            values: list[object] = [publicacion_id, total, estado]

            if "comprador_id" in columns:
                insert_columns.append("comprador_id")
                values.append(comprador_id)
            if "cantidad" in columns:
                insert_columns.append("cantidad")
                values.append(cantidad)
            if "usuario_id" in columns:
                insert_columns.append("usuario_id")
                values.append(comprador_id)
            if "telefono" in columns:
                insert_columns.append("telefono")
                values.append("")
            if "direccion_entrega" in columns:
                insert_columns.append("direccion_entrega")
                values.append("")
            if "created_at" in columns:
                insert_columns.append("created_at")
                values.append(datetime.now(timezone.utc).isoformat())

            placeholders = ", ".join(["?"] * len(insert_columns))
            sql = f"INSERT INTO orders ({', '.join(insert_columns)}) VALUES ({placeholders})"
            cursor = connection.execute(sql, values)
            connection.commit()
            order_id = int(cursor.lastrowid)
        order = self.get_order(order_id)
        assert order is not None
        return order

    def list_orders(self) -> list[Order]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, publicacion_id, comprador_id, cantidad, total, estado
                FROM orders
                ORDER BY id DESC
                """
            ).fetchall()
        return [self._map_order(r) for r in rows]

    def get_order(self, order_id: int) -> Order | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, publicacion_id, comprador_id, cantidad, total, estado
                FROM orders
                WHERE id = ?
                """,
                (order_id,),
            ).fetchone()
        return self._map_order(row) if row else None

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.database_path)
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def _map_publication(row: sqlite3.Row) -> Publication:
        return Publication(
            id=int(row["id"]),
            autor_id=int(row["autor_id"]),
            titulo=str(row["titulo"]),
            descripcion=str(row["descripcion"]),
            precio=float(row["precio"]),
            disponibilidad=bool(row["disponibilidad"]),
            direccion_texto=str(row["direccion_texto"]),
        )

    @staticmethod
    def _map_order(row: sqlite3.Row) -> Order:
        return Order(
            id=int(row["id"]),
            publicacion_id=int(row["publicacion_id"]),
            comprador_id=int(row["comprador_id"]),
            cantidad=int(row["cantidad"]),
            total=float(row["total"]),
            estado=str(row["estado"]),
        )
