from __future__ import annotations

from datetime import datetime, timezone

import psycopg
from psycopg.rows import dict_row

from ..models import Certificate, Rating, Transaction


class PostgresSupportRepository:
    def __init__(self, dsn: str, *, schema: str = "support_service") -> None:
        self.dsn = dsn
        self.schema = schema

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(f'CREATE SCHEMA IF NOT EXISTS "{self.schema}"')
            connection.execute(
                f"""
                CREATE TABLE IF NOT EXISTS "{self.schema}".ratings (
                    id SERIAL PRIMARY KEY,
                    usuario_id INTEGER NOT NULL,
                    autor_id INTEGER NOT NULL,
                    puntuacion INTEGER NOT NULL,
                    comentario TEXT NOT NULL,
                    fecha TEXT NOT NULL
                )
                """
            )
            connection.execute(
                f"""
                CREATE TABLE IF NOT EXISTS "{self.schema}".certificates (
                    id SERIAL PRIMARY KEY,
                    usuario_id INTEGER NOT NULL UNIQUE,
                    archivo_url TEXT NOT NULL,
                    fecha_emision TEXT NOT NULL,
                    estado_verificacion BOOLEAN NOT NULL DEFAULT FALSE
                )
                """
            )
            connection.execute(
                f"""
                CREATE TABLE IF NOT EXISTS "{self.schema}".transactions (
                    id SERIAL PRIMARY KEY,
                    pedido_id INTEGER NOT NULL UNIQUE,
                    fecha_cierre TEXT,
                    estado TEXT NOT NULL,
                    distancia_validacion_metros DOUBLE PRECISION NOT NULL DEFAULT 0
                )
                """
            )
            connection.commit()

    def create_rating(self, *, usuario_id: int, autor_id: int, puntuacion: int, comentario: str) -> Rating:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            row = connection.execute(
                f"""
                INSERT INTO "{self.schema}".ratings (usuario_id, autor_id, puntuacion, comentario, fecha)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, usuario_id, autor_id, puntuacion, comentario, fecha
                """,
                (usuario_id, autor_id, puntuacion, comentario, now),
            ).fetchone()
            connection.commit()
        return self._map_rating(row)

    def list_ratings_for_user(self, *, usuario_id: int) -> list[Rating]:
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT id, usuario_id, autor_id, puntuacion, comentario, fecha
                FROM "{self.schema}".ratings
                WHERE usuario_id = %s
                ORDER BY fecha DESC, id DESC
                """,
                (usuario_id,),
            ).fetchall()
        return [self._map_rating(row) for row in rows]

    def get_rating(self, rating_id: int) -> Rating | None:
        with self._connect() as connection:
            row = connection.execute(
                f"""
                SELECT id, usuario_id, autor_id, puntuacion, comentario, fecha
                FROM "{self.schema}".ratings
                WHERE id = %s
                """,
                (rating_id,),
            ).fetchone()
        return self._map_rating(row) if row else None

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
                f"""
                INSERT INTO "{self.schema}".certificates (usuario_id, archivo_url, fecha_emision, estado_verificacion)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (usuario_id) DO UPDATE SET
                    archivo_url = EXCLUDED.archivo_url,
                    fecha_emision = EXCLUDED.fecha_emision,
                    estado_verificacion = EXCLUDED.estado_verificacion
                """,
                (usuario_id, archivo_url, fecha_emision, estado_verificacion),
            )
            connection.commit()
        return self.get_certificate_by_user(usuario_id)

    def get_certificate_by_user(self, usuario_id: int) -> Certificate | None:
        with self._connect() as connection:
            row = connection.execute(
                f"""
                SELECT id, usuario_id, archivo_url, fecha_emision, estado_verificacion
                FROM "{self.schema}".certificates
                WHERE usuario_id = %s
                """,
                (usuario_id,),
            ).fetchone()
        return self._map_certificate(row) if row else None

    def upsert_transaction(
        self,
        *,
        pedido_id: int,
        fecha_cierre: str | None,
        estado: str,
        distancia_validacion_metros: float,
    ) -> Transaction:
        with self._connect() as connection:
            connection.execute(
                f"""
                INSERT INTO "{self.schema}".transactions (pedido_id, fecha_cierre, estado, distancia_validacion_metros)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (pedido_id) DO UPDATE SET
                    fecha_cierre = EXCLUDED.fecha_cierre,
                    estado = EXCLUDED.estado,
                    distancia_validacion_metros = EXCLUDED.distancia_validacion_metros
                """,
                (pedido_id, fecha_cierre, estado, distancia_validacion_metros),
            )
            connection.commit()
        return self.get_transaction_by_order(pedido_id)

    def get_transaction_by_order(self, pedido_id: int) -> Transaction | None:
        with self._connect() as connection:
            row = connection.execute(
                f"""
                SELECT id, pedido_id, fecha_cierre, estado, distancia_validacion_metros
                FROM "{self.schema}".transactions
                WHERE pedido_id = %s
                """,
                (pedido_id,),
            ).fetchone()
        return self._map_transaction(row) if row else None

    def _connect(self) -> psycopg.Connection:
        return psycopg.connect(self.dsn, row_factory=dict_row)

    @staticmethod
    def _map_rating(row: dict) -> Rating:
        return Rating(
            id=int(row["id"]),
            usuario_id=int(row["usuario_id"]),
            autor_id=int(row["autor_id"]),
            puntuacion=int(row["puntuacion"]),
            comentario=str(row["comentario"]),
            fecha=str(row["fecha"]),
        )

    @staticmethod
    def _map_certificate(row: dict) -> Certificate:
        return Certificate(
            id=int(row["id"]),
            usuario_id=int(row["usuario_id"]),
            archivo_url=str(row["archivo_url"]),
            fecha_emision=str(row["fecha_emision"]),
            estado_verificacion=bool(row["estado_verificacion"]),
        )

    @staticmethod
    def _map_transaction(row: dict) -> Transaction:
        return Transaction(
            id=int(row["id"]),
            pedido_id=int(row["pedido_id"]),
            fecha_cierre=row["fecha_cierre"],
            estado=str(row["estado"]),
            distancia_validacion_metros=float(row["distancia_validacion_metros"] or 0.0),
        )
