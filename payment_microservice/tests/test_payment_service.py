from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.errors import NotFoundError
from app.services.payment_service import PaymentService


@pytest.fixture
def repo():
    return MagicMock()


@pytest.fixture
def publisher():
    return MagicMock()


@pytest.fixture
def service(repo, publisher):
    return PaymentService(repository=repo, event_publisher=publisher)


def test_create_payment_authorized_publishes_event(service, repo, publisher):
    repo.update_status.return_value = MagicMock(estado="AUTORIZADO")

    result = service.create_payment(
        pedido_id="1", usuario_id=1, monto=20000.0, moneda="COP", metodo_pago="credit_card"
    )

    repo.create.assert_called_once()
    repo.update_status.assert_called_once()
    assert repo.update_status.call_args.kwargs["estado"] == "AUTORIZADO"
    publisher.publish_payment_processed.assert_called_once_with(result)


def test_create_payment_over_limit_is_declined(service, repo, publisher):
    repo.update_status.return_value = MagicMock(estado="FALLIDO")

    service.create_payment(
        pedido_id="1", usuario_id=1, monto=20_000_000.0, moneda="COP", metodo_pago="credit_card"
    )

    assert repo.update_status.call_args.kwargs["estado"] == "FALLIDO"
    assert "limite" in repo.update_status.call_args.kwargs["mensaje_estado"]


def test_create_payment_nequi_over_limit_is_declined(service, repo):
    repo.update_status.return_value = MagicMock(estado="FALLIDO")

    service.create_payment(
        pedido_id="1", usuario_id=1, monto=3_000_000.0, moneda="COP", metodo_pago="nequi"
    )

    assert repo.update_status.call_args.kwargs["estado"] == "FALLIDO"


def test_create_payment_nequi_within_limit_is_authorized(service, repo):
    repo.update_status.return_value = MagicMock(estado="AUTORIZADO")

    service.create_payment(
        pedido_id="1", usuario_id=1, monto=1_000_000.0, moneda="COP", metodo_pago="nequi"
    )

    assert repo.update_status.call_args.kwargs["estado"] == "AUTORIZADO"


def test_create_payment_raises_when_update_status_returns_none(service, repo):
    repo.update_status.return_value = None
    with pytest.raises(NotFoundError):
        service.create_payment(
            pedido_id="1", usuario_id=1, monto=1.0, moneda="COP", metodo_pago="credit_card"
        )


def test_create_payment_without_publisher_does_not_crash(repo):
    repo.update_status.return_value = MagicMock(estado="AUTORIZADO")
    service = PaymentService(repository=repo, event_publisher=None)

    result = service.create_payment(
        pedido_id="1", usuario_id=1, monto=1.0, moneda="COP", metodo_pago="credit_card"
    )

    assert result is not None


def test_get_payment_not_found_raises(service, repo):
    repo.get_by_id.return_value = None
    with pytest.raises(NotFoundError):
        service.get_payment("does-not-exist")


def test_get_payment_success(service, repo):
    repo.get_by_id.return_value = "payment"
    assert service.get_payment("id-1") == "payment"
