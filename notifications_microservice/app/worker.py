from __future__ import annotations

import json
import logging
import os
from pathlib import Path

import pika
from pika.exceptions import AMQPError

from .repositories.notification_repository import SQLiteNotificationRepository
from .services import NotificationService

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
LOGGER = logging.getLogger(__name__)


def _build_notification_service() -> tuple[NotificationService, SQLiteNotificationRepository]:
    database_path = os.getenv(
        "NOTIFICATIONS_DATABASE_PATH",
        str(Path(__file__).resolve().parent.parent / "data" / "notifications.db"),
    )
    repository = SQLiteNotificationRepository(database_path)
    repository.initialize()
    service = NotificationService(repository=repository)
    return service, repository


def _build_connection() -> pika.BlockingConnection:
    host = os.getenv("RABBITMQ_HOST", "rabbitmq")
    port = int(os.getenv("RABBITMQ_PORT", "5672"))
    user = os.getenv("RABBITMQ_USER", "guest")
    password = os.getenv("RABBITMQ_PASSWORD", "guest")

    credentials = pika.PlainCredentials(user, password)
    parameters = pika.ConnectionParameters(
        host=host,
        port=port,
        credentials=credentials,
        heartbeat=30,
        blocked_connection_timeout=5,
        connection_attempts=20,
        retry_delay=3,
    )
    return pika.BlockingConnection(parameters)


def main() -> None:
    queue_name = os.getenv("RABBITMQ_PAYMENTS_QUEUE", "payments.events")
    service, repository = _build_notification_service()

    connection = _build_connection()
    channel = connection.channel()
    channel.queue_declare(queue=queue_name, durable=True)
    channel.basic_qos(prefetch_count=1)

    LOGGER.info("notifications-worker listening on queue '%s'", queue_name)

    def _on_message(ch, method, _properties, body: bytes):
        try:
            payload = json.loads(body.decode("utf-8"))
            event_id = str(payload.get("event_id") or "").strip()
            if not event_id:
                LOGGER.warning("Dropping event without event_id")
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return

            if not repository.register_processed_event(event_id=event_id):
                LOGGER.info("Skipping duplicated event %s", event_id)
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return

            event_type = str(payload.get("event_type") or "")
            data = payload.get("data") or {}
            if event_type != "payment.processed":
                LOGGER.info("Ignoring unsupported event type %s", event_type)
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return

            usuario_id = int(data.get("usuario_id") or 0)
            estado = str(data.get("estado") or "DESCONOCIDO")
            pedido_id = str(data.get("pedido_id") or "")
            mensaje_estado = str(data.get("mensaje_estado") or "")
            message = (
                f"Pago para pedido {pedido_id}: {estado}. {mensaje_estado}".strip()
            )

            service.create_notification(
                usuario_id=usuario_id,
                tipo="pago",
                mensaje=message,
            )
            LOGGER.info("Processed payment event %s for user %s", event_id, usuario_id)
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            LOGGER.warning("Invalid event payload. Dropping message: %s", exc)
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as exc:  # pragma: no cover
            LOGGER.exception("Unexpected error while processing event: %s", exc)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    channel.basic_consume(queue=queue_name, on_message_callback=_on_message)

    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        LOGGER.info("Stopping notifications-worker")
    finally:
        if connection.is_open:
            connection.close()


if __name__ == "__main__":
    try:
        main()
    except AMQPError as exc:
        LOGGER.exception("Failed to start notifications-worker: %s", exc)
        raise
