from __future__ import annotations

from datetime import datetime, timezone

import psycopg
from psycopg.rows import dict_row

from ..models import Notification


class PostgresNotificationRepository:
    def __init__(self, dsn: str, *, schema: str = "notifications_service") -> None:
        self.dsn = dsn
        self.schema = schema

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(f'CREATE SCHEMA IF NOT EXISTS "{self.schema}"')
            connection.execute(
                f"""
                CREATE TABLE IF NOT EXISTS "{self.schema}".notifications (
                    id SERIAL PRIMARY KEY,
                    usuario_id INTEGER NOT NULL,
                    tipo TEXT NOT NULL,
                    mensaje TEXT NOT NULL,
                    fecha_envio TEXT NOT NULL,
                    leida BOOLEAN NOT NULL DEFAULT FALSE
                )
                """
            )
            connection.execute(
                f"""
                CREATE TABLE IF NOT EXISTS "{self.schema}".processed_events (
                    event_id TEXT PRIMARY KEY,
                    processed_at TEXT NOT NULL
                )
                """
            )
            connection.commit()

    def register_processed_event(self, *, event_id: str) -> bool:
        timestamp = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            cursor = connection.execute(
                f"""
                INSERT INTO "{self.schema}".processed_events (event_id, processed_at)
                VALUES (%s, %s)
                ON CONFLICT (event_id) DO NOTHING
                """,
                (event_id, timestamp),
            )
            connection.commit()
        return int(cursor.rowcount) > 0

    def create(self, *, usuario_id: int, tipo: str, mensaje: str) -> Notification:
        timestamp = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            row = connection.execute(
                f"""
                INSERT INTO "{self.schema}".notifications (usuario_id, tipo, mensaje, fecha_envio, leida)
                VALUES (%s, %s, %s, %s, FALSE)
                RETURNING id, usuario_id, tipo, mensaje, fecha_envio, leida
                """,
                (usuario_id, tipo, mensaje, timestamp),
            ).fetchone()
            connection.commit()
        return self._map_row(row)

    def list_by_user(self, *, usuario_id: int) -> list[Notification]:
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT id, usuario_id, tipo, mensaje, fecha_envio, leida
                FROM "{self.schema}".notifications
                WHERE usuario_id = %s
                ORDER BY fecha_envio DESC, id DESC
                """,
                (usuario_id,),
            ).fetchall()
        return [self._map_row(row) for row in rows]

    def get_by_id(self, notification_id: int) -> Notification | None:
        with self._connect() as connection:
            row = connection.execute(
                f"""
                SELECT id, usuario_id, tipo, mensaje, fecha_envio, leida
                FROM "{self.schema}".notifications
                WHERE id = %s
                """,
                (notification_id,),
            ).fetchone()
        return self._map_row(row) if row else None

    def mark_as_read(self, notification_id: int) -> Notification | None:
        with self._connect() as connection:
            connection.execute(
                f'UPDATE "{self.schema}".notifications SET leida = TRUE WHERE id = %s',
                (notification_id,),
            )
            connection.commit()
        return self.get_by_id(notification_id)

    def _connect(self) -> psycopg.Connection:
        return psycopg.connect(self.dsn, row_factory=dict_row)

    @staticmethod
    def _map_row(row: dict) -> Notification:
        return Notification(
            id=int(row["id"]),
            usuario_id=int(row["usuario_id"]),
            tipo=str(row["tipo"]),
            mensaje=str(row["mensaje"]),
            fecha_envio=str(row["fecha_envio"]),
            leida=bool(row["leida"]),
        )
