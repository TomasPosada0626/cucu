from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from ..models import Notification


class SQLiteNotificationRepository:
    def __init__(self, database_path: str) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    usuario_id INTEGER NOT NULL,
                    tipo TEXT NOT NULL,
                    mensaje TEXT NOT NULL,
                    fecha_envio TEXT NOT NULL,
                    leida INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS processed_events (
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
                """
                INSERT OR IGNORE INTO processed_events (event_id, processed_at)
                VALUES (?, ?)
                """,
                (event_id, timestamp),
            )
            connection.commit()
        return int(cursor.rowcount) > 0

    def create(self, *, usuario_id: int, tipo: str, mensaje: str) -> Notification:
        timestamp = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO notifications (usuario_id, tipo, mensaje, fecha_envio, leida)
                VALUES (?, ?, ?, ?, 0)
                """,
                (usuario_id, tipo, mensaje, timestamp),
            )
            connection.commit()
            notification_id = int(cursor.lastrowid)
        return self.get_by_id(notification_id)

    def list_by_user(self, *, usuario_id: int) -> list[Notification]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, usuario_id, tipo, mensaje, fecha_envio, leida
                FROM notifications
                WHERE usuario_id = ?
                ORDER BY fecha_envio DESC, id DESC
                """,
                (usuario_id,),
            ).fetchall()
        return [self._map_row(row) for row in rows]

    def get_by_id(self, notification_id: int) -> Notification | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, usuario_id, tipo, mensaje, fecha_envio, leida
                FROM notifications
                WHERE id = ?
                """,
                (notification_id,),
            ).fetchone()
        if row is None:
            return None
        return self._map_row(row)

    def mark_as_read(self, notification_id: int) -> Notification | None:
        with self._connect() as connection:
            connection.execute("UPDATE notifications SET leida = 1 WHERE id = ?", (notification_id,))
            connection.commit()
        return self.get_by_id(notification_id)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.database_path)
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def _map_row(row: sqlite3.Row) -> Notification:
        return Notification(
            id=int(row["id"]),
            usuario_id=int(row["usuario_id"]),
            tipo=str(row["tipo"]),
            mensaje=str(row["mensaje"]),
            fecha_envio=str(row["fecha_envio"]),
            leida=bool(row["leida"]),
        )
