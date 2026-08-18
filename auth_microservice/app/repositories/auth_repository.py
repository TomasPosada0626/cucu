from __future__ import annotations

import psycopg
from psycopg.rows import dict_row

from ..models import User


class PostgresAuthRepository:
    def __init__(self, dsn: str, *, schema: str = "auth_service") -> None:
        self.dsn = dsn
        self.schema = schema

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(f'CREATE SCHEMA IF NOT EXISTS "{self.schema}"')
            connection.execute(
                f"""
                CREATE TABLE IF NOT EXISTS "{self.schema}".users (
                    id SERIAL PRIMARY KEY,
                    username TEXT NOT NULL UNIQUE,
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    is_active BOOLEAN NOT NULL DEFAULT TRUE
                )
                """
            )
            connection.commit()

    def create_user(self, *, username: str, email: str, password_hash: str) -> User:
        with self._connect() as connection:
            row = connection.execute(
                f"""
                INSERT INTO "{self.schema}".users (username, email, password_hash)
                VALUES (%s, %s, %s)
                RETURNING id, username, email, password_hash, is_active
                """,
                (username, email, password_hash),
            ).fetchone()
            connection.commit()
        return self._map_row(row)

    def get_user_by_id(self, user_id: int) -> User | None:
        with self._connect() as connection:
            row = connection.execute(
                f'SELECT id, username, email, password_hash, is_active FROM "{self.schema}".users WHERE id = %s',
                (user_id,),
            ).fetchone()
        return self._map_row(row) if row else None

    def get_user_by_email(self, email: str) -> User | None:
        with self._connect() as connection:
            row = connection.execute(
                f'SELECT id, username, email, password_hash, is_active FROM "{self.schema}".users '
                "WHERE lower(email) = lower(%s)",
                (email,),
            ).fetchone()
        return self._map_row(row) if row else None

    def get_user_by_username(self, username: str) -> User | None:
        with self._connect() as connection:
            row = connection.execute(
                f'SELECT id, username, email, password_hash, is_active FROM "{self.schema}".users '
                "WHERE lower(username) = lower(%s)",
                (username,),
            ).fetchone()
        return self._map_row(row) if row else None

    def _connect(self) -> psycopg.Connection:
        return psycopg.connect(self.dsn, row_factory=dict_row)

    @staticmethod
    def _map_row(row: dict) -> User:
        return User(
            id=int(row["id"]),
            username=str(row["username"]),
            email=str(row["email"]),
            password_hash=str(row["password_hash"]),
            is_active=bool(row["is_active"]),
        )
