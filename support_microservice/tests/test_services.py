from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.errors import NotFoundError, ValidationError
from app.services import SupportService


@pytest.fixture
def repo():
    return MagicMock()


@pytest.fixture
def service(repo):
    return SupportService(repository=repo)


def test_create_rating_rejects_missing_usuario_or_autor(service):
    with pytest.raises(ValidationError):
        service.create_rating(usuario_id=0, autor_id=1, puntuacion=5, comentario="x")
    with pytest.raises(ValidationError):
        service.create_rating(usuario_id=1, autor_id=0, puntuacion=5, comentario="x")


def test_create_rating_rejects_out_of_range_puntuacion(service):
    with pytest.raises(ValidationError):
        service.create_rating(usuario_id=1, autor_id=2, puntuacion=0, comentario="x")
    with pytest.raises(ValidationError):
        service.create_rating(usuario_id=1, autor_id=2, puntuacion=6, comentario="x")


def test_create_rating_rejects_blank_comentario(service):
    with pytest.raises(ValidationError):
        service.create_rating(usuario_id=1, autor_id=2, puntuacion=5, comentario="   ")


def test_create_rating_success(service, repo):
    repo.create_rating.return_value.to_dict.return_value = {"id": 1}
    result = service.create_rating(usuario_id=1, autor_id=2, puntuacion=5, comentario=" Bien ")
    assert result == {"id": 1}
    repo.create_rating.assert_called_once_with(usuario_id=1, autor_id=2, puntuacion=5, comentario="Bien")


def test_list_ratings_rejects_invalid_usuario(service):
    with pytest.raises(ValidationError):
        service.list_ratings(usuario_id=0)


def test_list_ratings_success(service, repo):
    item = MagicMock()
    item.to_dict.return_value = {"id": 1}
    repo.list_ratings_for_user.return_value = [item]
    assert service.list_ratings(usuario_id=1) == [{"id": 1}]


def test_upsert_certificate_rejects_invalid_usuario(service):
    with pytest.raises(ValidationError):
        service.upsert_certificate(usuario_id=0, archivo_url="x", fecha_emision="y", estado_verificacion=True)


def test_upsert_certificate_rejects_blank_archivo_url(service):
    with pytest.raises(ValidationError):
        service.upsert_certificate(usuario_id=1, archivo_url="  ", fecha_emision="y", estado_verificacion=True)


def test_upsert_certificate_rejects_blank_fecha_emision(service):
    with pytest.raises(ValidationError):
        service.upsert_certificate(usuario_id=1, archivo_url="x", fecha_emision="  ", estado_verificacion=True)


def test_upsert_certificate_success(service, repo):
    repo.upsert_certificate.return_value.to_dict.return_value = {"id": 1}
    result = service.upsert_certificate(
        usuario_id=1, archivo_url="url", fecha_emision="2026-01-01", estado_verificacion=True
    )
    assert result == {"id": 1}


def test_get_certificate_not_found_raises(service, repo):
    repo.get_certificate_by_user.return_value = None
    with pytest.raises(NotFoundError):
        service.get_certificate(usuario_id=1)


def test_get_certificate_success(service, repo):
    repo.get_certificate_by_user.return_value.to_dict.return_value = {"id": 1}
    assert service.get_certificate(usuario_id=1) == {"id": 1}


def test_upsert_transaction_rejects_invalid_pedido_id(service):
    with pytest.raises(ValidationError):
        service.upsert_transaction(pedido_id=0, fecha_cierre=None, estado="ABIERTA", distancia_validacion_metros=0)


def test_upsert_transaction_defaults_estado_when_blank(service, repo):
    repo.upsert_transaction.return_value.to_dict.return_value = {"id": 1}
    service.upsert_transaction(pedido_id=1, fecha_cierre=None, estado="  ", distancia_validacion_metros=0)
    assert repo.upsert_transaction.call_args.kwargs["estado"] == "ABIERTA"


def test_upsert_transaction_normalizes_estado_uppercase(service, repo):
    repo.upsert_transaction.return_value.to_dict.return_value = {"id": 1}
    service.upsert_transaction(pedido_id=1, fecha_cierre=" x ", estado="cerrada", distancia_validacion_metros=1)
    assert repo.upsert_transaction.call_args.kwargs["estado"] == "CERRADA"
    assert repo.upsert_transaction.call_args.kwargs["fecha_cierre"] == "x"


def test_get_transaction_rejects_non_numeric_pedido_id(service):
    with pytest.raises(ValidationError):
        service.get_transaction(pedido_id="abc")


def test_get_transaction_rejects_non_positive_pedido_id(service):
    with pytest.raises(ValidationError):
        service.get_transaction(pedido_id=0)


def test_get_transaction_not_found_raises(service, repo):
    repo.get_transaction_by_order.return_value = None
    with pytest.raises(NotFoundError):
        service.get_transaction(pedido_id=1)


def test_get_transaction_success(service, repo):
    repo.get_transaction_by_order.return_value.to_dict.return_value = {"id": 1}
    assert service.get_transaction(pedido_id=1) == {"id": 1}
