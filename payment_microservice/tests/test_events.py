from __future__ import annotations

from unittest import mock

from pika.exceptions import AMQPError

from app.events import RabbitMQPaymentEventPublisher
from app.models import Payment


def _payment():
    return Payment(
        id="pay-1",
        pedido_id="77",
        usuario_id=1,
        monto=1000.0,
        moneda="COP",
        metodo_pago="credit_card",
        estado="AUTORIZADO",
        mensaje_estado="ok",
        creado_en="now",
        actualizado_en="now",
    )


def test_reads_config_from_env(monkeypatch):
    monkeypatch.setenv("RABBITMQ_HOST", "custom-host")
    monkeypatch.setenv("RABBITMQ_PORT", "5673")
    monkeypatch.setenv("RABBITMQ_PAYMENTS_QUEUE", "custom.queue")

    publisher = RabbitMQPaymentEventPublisher()

    assert publisher.host == "custom-host"
    assert publisher.port == 5673
    assert publisher.queue == "custom.queue"


def test_publish_payment_processed_success():
    channel = mock.MagicMock()
    connection = mock.MagicMock()
    connection.channel.return_value = channel

    publisher = RabbitMQPaymentEventPublisher()
    with mock.patch("app.events.pika.BlockingConnection", return_value=connection):
        publisher.publish_payment_processed(_payment())

    channel.queue_declare.assert_called_once_with(queue=publisher.queue, durable=True)
    channel.basic_publish.assert_called_once()
    connection.close.assert_called_once()


def test_publish_payment_processed_swallows_amqp_error():
    publisher = RabbitMQPaymentEventPublisher()
    with mock.patch("app.events.pika.BlockingConnection", side_effect=AMQPError("down")):
        # No debe propagar la excepcion: un fallo al publicar el evento no
        # debe tumbar la respuesta HTTP del pago ya procesado.
        publisher.publish_payment_processed(_payment())
