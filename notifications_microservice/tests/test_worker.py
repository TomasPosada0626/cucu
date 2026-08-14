from __future__ import annotations

import json
from unittest import mock

import pytest


@pytest.fixture
def worker_env(tmp_path, monkeypatch):
    monkeypatch.setenv("NOTIFICATIONS_DATABASE_PATH", str(tmp_path / "worker.db"))


def _run_main_and_capture_callback(monkeypatch):
    """Corre app.worker.main() con pika mockeado (start_consuming levanta
    KeyboardInterrupt de inmediato) y devuelve el callback on_message real
    que quedo registrado, para poder invocarlo directo en los tests."""
    from app import worker

    channel = mock.MagicMock()
    channel.start_consuming.side_effect = KeyboardInterrupt()
    connection = mock.MagicMock()
    connection.channel.return_value = channel
    connection.is_open = True

    monkeypatch.setattr(worker.pika, "BlockingConnection", mock.MagicMock(return_value=connection))

    worker.main()

    _, kwargs = channel.basic_consume.call_args
    return kwargs["on_message_callback"], channel


def test_main_declares_queue_and_consumes_then_stops_on_interrupt(worker_env, monkeypatch):
    callback, channel = _run_main_and_capture_callback(monkeypatch)
    assert callable(callback)
    channel.queue_declare.assert_called_once()
    channel.basic_qos.assert_called_once_with(prefetch_count=1)


def test_on_message_drops_event_without_event_id(worker_env, monkeypatch):
    callback, channel = _run_main_and_capture_callback(monkeypatch)
    method = mock.MagicMock(delivery_tag=1)

    callback(channel, method, None, json.dumps({"event_type": "payment.processed"}).encode())

    channel.basic_ack.assert_called_once_with(delivery_tag=1)


def test_on_message_skips_duplicate_event(worker_env, monkeypatch):
    callback, channel = _run_main_and_capture_callback(monkeypatch)
    method = mock.MagicMock(delivery_tag=2)
    body = json.dumps({
        "event_id": "evt-dup",
        "event_type": "payment.processed",
        "data": {"usuario_id": 1, "estado": "AUTORIZADO", "pedido_id": "1", "mensaje_estado": ""},
    }).encode()

    callback(channel, method, None, body)
    callback(channel, method, None, body)

    assert channel.basic_ack.call_count == 2
    channel.basic_nack.assert_not_called()


def test_on_message_ignores_unsupported_event_type(worker_env, monkeypatch):
    callback, channel = _run_main_and_capture_callback(monkeypatch)
    method = mock.MagicMock(delivery_tag=3)
    body = json.dumps({"event_id": "evt-other", "event_type": "order.created", "data": {}}).encode()

    callback(channel, method, None, body)

    channel.basic_ack.assert_called_once_with(delivery_tag=3)


def test_on_message_creates_notification_for_payment_processed(worker_env, monkeypatch):
    callback, channel = _run_main_and_capture_callback(monkeypatch)
    method = mock.MagicMock(delivery_tag=4)
    body = json.dumps({
        "event_id": "evt-ok",
        "event_type": "payment.processed",
        "data": {"usuario_id": 1, "estado": "AUTORIZADO", "pedido_id": "77", "mensaje_estado": "Todo bien"},
    }).encode()

    callback(channel, method, None, body)

    channel.basic_ack.assert_called_once_with(delivery_tag=4)

    from app.repositories.notification_repository import SQLiteNotificationRepository
    import os

    repo = SQLiteNotificationRepository(os.environ["NOTIFICATIONS_DATABASE_PATH"])
    items = repo.list_by_user(usuario_id=1)
    assert len(items) == 1
    assert "77" in items[0].mensaje


def test_on_message_drops_invalid_json_body(worker_env, monkeypatch):
    callback, channel = _run_main_and_capture_callback(monkeypatch)
    method = mock.MagicMock(delivery_tag=5)

    callback(channel, method, None, b"not json")

    channel.basic_ack.assert_called_once_with(delivery_tag=5)


def test_on_message_nacks_on_unexpected_error(worker_env, monkeypatch):
    from app.services import NotificationService

    monkeypatch.setattr(
        NotificationService,
        "create_notification",
        lambda self, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    callback, channel = _run_main_and_capture_callback(monkeypatch)
    method = mock.MagicMock(delivery_tag=6)
    body = json.dumps({
        "event_id": "evt-boom",
        "event_type": "payment.processed",
        "data": {"usuario_id": 1, "estado": "AUTORIZADO", "pedido_id": "1", "mensaje_estado": ""},
    }).encode()

    callback(channel, method, None, body)

    channel.basic_nack.assert_called_once_with(delivery_tag=6, requeue=False)


def test_build_connection_uses_env_vars(worker_env, monkeypatch):
    from app import worker

    monkeypatch.setenv("RABBITMQ_HOST", "custom-host")
    monkeypatch.setenv("RABBITMQ_PORT", "5673")
    captured = {}

    def _fake_blocking_connection(parameters):
        captured["params"] = parameters
        return mock.MagicMock()

    monkeypatch.setattr(worker.pika, "BlockingConnection", _fake_blocking_connection)

    worker._build_connection()

    assert captured["params"].host == "custom-host"
    assert captured["params"].port == 5673
