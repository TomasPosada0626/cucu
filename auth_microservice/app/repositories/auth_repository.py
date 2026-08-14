from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from ..models import User


class SQLiteAuthRepository:
    def __init__(self, database_path: str) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    is_active INTEGER NOT NULL DEFAULT 1
                )
                """
            )
            self._ensure_schema_compatibility(connection)
            connection.commit()

    def _ensure_schema_compatibility(self, connection: sqlite3.Connection) -> None:
        columns = self._get_columns(connection, "users")

        # Las consultas de lectura usan COALESCE(username, nombre, '') para
        # tolerar tablas viejas de Django (que usan 'nombre'); si la tabla es
        # nueva y nunca tuvo esa columna, el SELECT falla con "no such column:
        # nombre" salvo que la garanticemos aqui tambien.
        if "nombre" not in columns:
            connection.execute("ALTER TABLE users ADD COLUMN nombre TEXT")

        if "username" not in columns:
            connection.execute("ALTER TABLE users ADD COLUMN username TEXT")
            connection.execute(
                "UPDATE users SET username = 'user_' || id WHERE username IS NULL OR trim(username) = ''"
            )

        if "email" not in columns:
            connection.execute("ALTER TABLE users ADD COLUMN email TEXT")
            connection.execute(
                "UPDATE users SET email = username || '@local.invalid' WHERE email IS NULL OR trim(email) = ''"
            )

        if "password_hash" not in columns:
            connection.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")

        if "is_active" not in columns:
            connection.execute("ALTER TABLE users ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1")

    @staticmethod
    def _get_columns(connection: sqlite3.Connection, table_name: str) -> set[str]:
        rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
        return {str(row[1]) for row in rows}

    def create_user(self, *, username: str, email: str, password_hash: str) -> User:
        with self._connect() as connection:
            columns = self._get_columns(connection, "users")
            insert_columns: list[str] = ["email", "password_hash"]
            values: list[object] = [email, password_hash]

            if "is_active" in columns:
                insert_columns.append("is_active")
                values.append(1)
            if "username" in columns:
                insert_columns.append("username")
                values.append(username)
            if "nombre" in columns:
                insert_columns.append("nombre")
                values.append(username)
            if "fecha_registro" in columns:
                insert_columns.append("fecha_registro")
                values.append(datetime.now(timezone.utc).isoformat())

            placeholders = ", ".join(["?"] * len(insert_columns))
            sql = f"INSERT INTO users ({', '.join(insert_columns)}) VALUES ({placeholders})"
            cursor = connection.execute(sql, values)
            connection.commit()
            user_id = int(cursor.lastrowid)
        user = self.get_user_by_id(user_id)
        assert user is not None
        return user

    def get_user_by_id(self, user_id: int) -> User | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    id,
                    COALESCE(username, nombre, '') AS username,
                    email,
                    password_hash,
                    COALESCE(is_active, 1) AS is_active
                FROM users
                WHERE id = ?
                """,
                (user_id,),
            ).fetchone()
        return self._map_row(row) if row else None

    def get_user_by_email(self, email: str) -> User | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    id,
                    COALESCE(username, nombre, '') AS username,
                    email,
                    password_hash,
                    COALESCE(is_active, 1) AS is_active
                FROM users
                WHERE lower(email) = lower(?)
                """,
                (email,),
            ).fetchone()
        return self._map_row(row) if row else None

    def get_user_by_username(self, username: str) -> User | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    id,
                    COALESCE(username, nombre, '') AS username,
                    email,
                    password_hash,
                    COALESCE(is_active, 1) AS is_active
                FROM users
                WHERE lower(COALESCE(username, nombre, '')) = lower(?)
                """,
                (username,),
            ).fetchone()
        return self._map_row(row) if row else None

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.database_path)
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def _map_row(row: sqlite3.Row) -> User:
        return User(
            id=int(row["id"]),
            username=str(row["username"]),
            email=str(row["email"]),
            password_hash=str(row["password_hash"]),
            is_active=bool(row["is_active"]),
        )
