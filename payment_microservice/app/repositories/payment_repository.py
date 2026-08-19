from __future__ import annotations

import psycopg
from psycopg.rows import dict_row

from ..models import Payment


class PostgresPaymentRepository:
    def __init__(self, dsn: str, *, schema: str = "payment_service") -> None:
        self.dsn = dsn
        self.schema = schema

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(f'CREATE SCHEMA IF NOT EXISTS "{self.schema}"')
            connection.execute(
                f"""
                CREATE TABLE IF NOT EXISTS "{self.schema}".payments (
                    id TEXT PRIMARY KEY,
                    pedido_id TEXT NOT NULL,
                    usuario_id INTEGER NOT NULL,
                    monto DOUBLE PRECISION NOT NULL,
                    moneda TEXT NOT NULL,
                    metodo_pago TEXT NOT NULL,
                    estado TEXT NOT NULL,
                    mensaje_estado TEXT NOT NULL,
                    creado_en TEXT NOT NULL,
                    actualizado_en TEXT NOT NULL
                )
                """
            )
            connection.commit()

    def create(self, payment: Payment) -> Payment:
        with self._connect() as connection:
            connection.execute(
                f"""
                INSERT INTO "{self.schema}".payments (
                    id, pedido_id, usuario_id, monto, moneda,
                    metodo_pago, estado, mensaje_estado, creado_en, actualizado_en
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    payment.id,
                    payment.pedido_id,
                    payment.usuario_id,
                    payment.monto,
                    payment.moneda,
                    payment.metodo_pago,
                    payment.estado,
                    payment.mensaje_estado,
                    payment.creado_en,
                    payment.actualizado_en,
                ),
            )
            connection.commit()
        return payment

    def get_by_id(self, payment_id: str) -> Payment | None:
        with self._connect() as connection:
            row = connection.execute(
                f"""
                SELECT id, pedido_id, usuario_id, monto, moneda,
                    metodo_pago, estado, mensaje_estado, creado_en, actualizado_en
                FROM "{self.schema}".payments
                WHERE id = %s
                """,
                (payment_id,),
            ).fetchone()

        return self._map_row(row) if row else None

    def update_status(
        self,
        payment_id: str,
        *,
        estado: str,
        mensaje_estado: str,
        actualizado_en: str,
    ) -> Payment | None:
        with self._connect() as connection:
            cursor = connection.execute(
                f"""
                UPDATE "{self.schema}".payments
                SET estado = %s, mensaje_estado = %s, actualizado_en = %s
                WHERE id = %s
                """,
                (estado, mensaje_estado, actualizado_en, payment_id),
            )
            connection.commit()

        if cursor.rowcount == 0:
            return None

        return self.get_by_id(payment_id)

    def _connect(self) -> psycopg.Connection:
        return psycopg.connect(self.dsn, row_factory=dict_row)

    @staticmethod
    def _map_row(row: dict) -> Payment:
        return Payment(
            id=row["id"],
            pedido_id=row["pedido_id"],
            usuario_id=row["usuario_id"],
            monto=row["monto"],
            moneda=row["moneda"],
            metodo_pago=row["metodo_pago"],
            estado=row["estado"],
            mensaje_estado=row["mensaje_estado"],
            creado_en=row["creado_en"],
            actualizado_en=row["actualizado_en"],
        )
