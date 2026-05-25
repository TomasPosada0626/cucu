from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from ..models import Certificate, Rating, Transaction


class SQLiteSupportRepository:
    def __init__(self, database_path: str) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS ratings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    usuario_id INTEGER NOT NULL,
                    autor_id INTEGER NOT NULL,
                    puntuacion INTEGER NOT NULL,
                    comentario TEXT NOT NULL,
                    fecha TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS certificates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    usuario_id INTEGER NOT NULL UNIQUE,
                    archivo_url TEXT NOT NULL,
                    fecha_emision TEXT NOT NULL,
                    estado_verificacion INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pedido_id INTEGER NOT NULL UNIQUE,
                    fecha_cierre TEXT,
                    estado TEXT NOT NULL,
                    distancia_validacion_metros REAL NOT NULL DEFAULT 0
                )
                """
            )
            self._ensure_schema_compatibility(connection)
            connection.commit()

    def _ensure_schema_compatibility(self, connection: sqlite3.Connection) -> None:
        transaction_columns = self._get_columns(connection, "transactions")
        if "fecha_cierre" not in transaction_columns:
            connection.execute("ALTER TABLE transactions ADD COLUMN fecha_cierre TEXT")

    @staticmethod
    def _get_columns(connection: sqlite3.Connection, table_name: str) -> set[str]:
        rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
        return {str(row[1]) for row in rows}

    def create_rating(self, *, usuario_id: int, autor_id: int, puntuacion: int, comentario: str) -> Rating:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO ratings (usuario_id, autor_id, puntuacion, comentario, fecha)
                VALUES (?, ?, ?, ?, ?)
                """,
                (usuario_id, autor_id, puntuacion, comentario, now),
            )
            connection.commit()
            rating_id = int(cursor.lastrowid)
        return self.get_rating(rating_id)

    def list_ratings_for_user(self, *, usuario_id: int) -> list[Rating]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, usuario_id, autor_id, puntuacion, comentario, fecha
                FROM ratings
                WHERE usuario_id = ?
                ORDER BY fecha DESC, id DESC
                """,
                (usuario_id,),
            ).fetchall()
        return [self._map_rating(row) for row in rows]

    def get_rating(self, rating_id: int) -> Rating | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, usuario_id, autor_id, puntuacion, comentario, fecha
                FROM ratings
                WHERE id = ?
                """,
                (rating_id,),
            ).fetchone()
        if row is None:
            return None
        return self._map_rating(row)

    def upsert_certificate(
        self,
        *,
        usuario_id: int,
        archivo_url: str,
        fecha_emision: str,
        estado_verificacion: bool,
    ) -> Certificate:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO certificates (usuario_id, archivo_url, fecha_emision, estado_verificacion)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(usuario_id) DO UPDATE SET
                    archivo_url=excluded.archivo_url,
                    fecha_emision=excluded.fecha_emision,
                    estado_verificacion=excluded.estado_verificacion
                """,
                (usuario_id, archivo_url, fecha_emision, 1 if estado_verificacion else 0),
            )
            connection.commit()
        return self.get_certificate_by_user(usuario_id)

    def get_certificate_by_user(self, usuario_id: int) -> Certificate | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, usuario_id, archivo_url, fecha_emision, estado_verificacion
                FROM certificates
                WHERE usuario_id = ?
                """,
                (usuario_id,),
            ).fetchone()
        if row is None:
            return None
        return self._map_certificate(row)

    def upsert_transaction(
        self,
        *,
        pedido_id: int,
        fecha_cierre: str | None,
        estado: str,
        distancia_validacion_metros: float,
    ) -> Transaction:
        with self._connect() as connection:
            existing = connection.execute(
                "SELECT id FROM transactions WHERE pedido_id = ?",
                (pedido_id,),
            ).fetchone()
            if existing:
                connection.execute(
                    """
                    UPDATE transactions
                    SET fecha_cierre = ?, estado = ?, distancia_validacion_metros = ?
                    WHERE pedido_id = ?
                    """,
                    (fecha_cierre, estado, distancia_validacion_metros, pedido_id),
                )
            else:
                now = datetime.now(timezone.utc).isoformat()
                columns = self._get_columns(connection, "transactions")
                insert_columns: list[str] = ["pedido_id", "estado", "distancia_validacion_metros"]
                values: list[object] = [pedido_id, estado, distancia_validacion_metros]
                if "fecha_cierre" in columns:
                    insert_columns.append("fecha_cierre")
                    values.append(fecha_cierre)
                if "created_at" in columns:
                    insert_columns.append("created_at")
                    values.append(now)

                placeholders = ", ".join(["?"] * len(insert_columns))
                sql = f"INSERT INTO transactions ({', '.join(insert_columns)}) VALUES ({placeholders})"
                connection.execute(sql, values)
            connection.commit()
        return self.get_transaction_by_order(pedido_id)

    def get_transaction_by_order(self, pedido_id: int) -> Transaction | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, pedido_id, fecha_cierre, estado, distancia_validacion_metros
                FROM transactions
                WHERE pedido_id = ?
                """,
                (pedido_id,),
            ).fetchone()
        if row is None:
            return None
        return self._map_transaction(row)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.database_path)
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def _map_rating(row: sqlite3.Row) -> Rating:
        return Rating(
            id=int(row["id"]),
            usuario_id=int(row["usuario_id"]),
            autor_id=int(row["autor_id"]),
            puntuacion=int(row["puntuacion"]),
            comentario=str(row["comentario"]),
            fecha=str(row["fecha"]),
        )

    @staticmethod
    def _map_certificate(row: sqlite3.Row) -> Certificate:
        return Certificate(
            id=int(row["id"]),
            usuario_id=int(row["usuario_id"]),
            archivo_url=str(row["archivo_url"]),
            fecha_emision=str(row["fecha_emision"]),
            estado_verificacion=bool(row["estado_verificacion"]),
        )

    @staticmethod
    def _map_transaction(row: sqlite3.Row) -> Transaction:
        return Transaction(
            id=int(row["id"]),
            pedido_id=int(row["pedido_id"]),
            fecha_cierre=row["fecha_cierre"],
            estado=str(row["estado"]),
            distancia_validacion_metros=float(row["distancia_validacion_metros"] or 0.0),
        )
