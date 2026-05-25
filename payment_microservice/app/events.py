from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from uuid import uuid4

import pika
from pika.exceptions import AMQPError

from .models import Payment

LOGGER = logging.getLogger(__name__)


class RabbitMQPaymentEventPublisher:
    def __init__(self) -> None:
        self.host = os.getenv("RABBITMQ_HOST", "rabbitmq")
        self.port = int(os.getenv("RABBITMQ_PORT", "5672"))
        self.user = os.getenv("RABBITMQ_USER", "guest")
        self.password = os.getenv("RABBITMQ_PASSWORD", "guest")
        self.queue = os.getenv("RABBITMQ_PAYMENTS_QUEUE", "payments.events")

    def publish_payment_processed(self, payment: Payment) -> None:
        event_payload = {
            "event_id": str(uuid4()),
            "event_type": "payment.processed",
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "data": {
                "payment_id": payment.id,
                "pedido_id": payment.pedido_id,
                "usuario_id": payment.usuario_id,
                "monto": payment.monto,
                "moneda": payment.moneda,
                "metodo_pago": payment.metodo_pago,
                "estado": payment.estado,
                "mensaje_estado": payment.mensaje_estado,
            },
        }

        credentials = pika.PlainCredentials(self.user, self.password)
        parameters = pika.ConnectionParameters(
            host=self.host,
            port=self.port,
            credentials=credentials,
            heartbeat=30,
            blocked_connection_timeout=5,
            connection_attempts=3,
            retry_delay=2,
        )

        try:
            connection = pika.BlockingConnection(parameters)
            channel = connection.channel()
            channel.queue_declare(queue=self.queue, durable=True)
            channel.basic_publish(
                exchange="",
                routing_key=self.queue,
                body=json.dumps(event_payload).encode("utf-8"),
                properties=pika.BasicProperties(
                    delivery_mode=2,
                    content_type="application/json",
                ),
            )
            connection.close()
        except AMQPError as exc:
            LOGGER.warning("Failed to publish payment event: %s", exc)
