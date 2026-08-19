from __future__ import annotations

import psycopg
from psycopg.rows import dict_row

from ..models import Order, Publication


class PostgresMarketRepository:
    def __init__(self, dsn: str, *, schema: str = "market_service") -> None:
        self.dsn = dsn
        self.schema = schema

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(f'CREATE SCHEMA IF NOT EXISTS "{self.schema}"')
            connection.execute(
                f"""
                CREATE TABLE IF NOT EXISTS "{self.schema}".publications (
                    id SERIAL PRIMARY KEY,
                    autor_id INTEGER NOT NULL,
                    titulo TEXT NOT NULL,
                    descripcion TEXT NOT NULL,
                    precio DOUBLE PRECISION NOT NULL,
                    disponibilidad BOOLEAN NOT NULL DEFAULT TRUE,
                    direccion_texto TEXT NOT NULL
                )
                """
            )
            connection.execute(
                f"""
                CREATE TABLE IF NOT EXISTS "{self.schema}".orders (
                    id SERIAL PRIMARY KEY,
                    publicacion_id INTEGER NOT NULL REFERENCES "{self.schema}".publications(id),
                    comprador_id INTEGER NOT NULL,
                    cantidad INTEGER NOT NULL,
                    total DOUBLE PRECISION NOT NULL,
                    estado TEXT NOT NULL
                )
                """
            )
            connection.commit()

    def create_publication(
        self, *, autor_id: int, titulo: str, descripcion: str, precio: float, direccion_texto: str
    ) -> Publication:
        with self._connect() as connection:
            row = connection.execute(
                f"""
                INSERT INTO "{self.schema}".publications
                    (autor_id, titulo, descripcion, precio, disponibilidad, direccion_texto)
                VALUES (%s, %s, %s, %s, TRUE, %s)
                RETURNING id, autor_id, titulo, descripcion, precio, disponibilidad, direccion_texto
                """,
                (autor_id, titulo, descripcion, precio, direccion_texto),
            ).fetchone()
            connection.commit()
        return self._map_publication(row)

    def list_publications(self) -> list[Publication]:
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT id, autor_id, titulo, descripcion, precio, disponibilidad, direccion_texto
                FROM "{self.schema}".publications
                ORDER BY id DESC
                """
            ).fetchall()
        return [self._map_publication(r) for r in rows]

    def get_publication(self, publication_id: int) -> Publication | None:
        with self._connect() as connection:
            row = connection.execute(
                f"""
                SELECT id, autor_id, titulo, descripcion, precio, disponibilidad, direccion_texto
                FROM "{self.schema}".publications
                WHERE id = %s
                """,
                (publication_id,),
            ).fetchone()
        return self._map_publication(row) if row else None

    def create_order(
        self, *, publicacion_id: int, comprador_id: int, cantidad: int, total: float, estado: str
    ) -> Order:
        with self._connect() as connection:
            row = connection.execute(
                f"""
                INSERT INTO "{self.schema}".orders (publicacion_id, comprador_id, cantidad, total, estado)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, publicacion_id, comprador_id, cantidad, total, estado
                """,
                (publicacion_id, comprador_id, cantidad, total, estado),
            ).fetchone()
            connection.commit()
        return self._map_order(row)

    def list_orders(self) -> list[Order]:
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT id, publicacion_id, comprador_id, cantidad, total, estado
                FROM "{self.schema}".orders
                ORDER BY id DESC
                """
            ).fetchall()
        return [self._map_order(r) for r in rows]

    def get_order(self, order_id: int) -> Order | None:
        with self._connect() as connection:
            row = connection.execute(
                f"""
                SELECT id, publicacion_id, comprador_id, cantidad, total, estado
                FROM "{self.schema}".orders
                WHERE id = %s
                """,
                (order_id,),
            ).fetchone()
        return self._map_order(row) if row else None

    def _connect(self) -> psycopg.Connection:
        return psycopg.connect(self.dsn, row_factory=dict_row)

    @staticmethod
    def _map_publication(row: dict) -> Publication:
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
    def _map_order(row: dict) -> Order:
        return Order(
            id=int(row["id"]),
            publicacion_id=int(row["publicacion_id"]),
            comprador_id=int(row["comprador_id"]),
            cantidad=int(row["cantidad"]),
            total=float(row["total"]),
            estado=str(row["estado"]),
        )
