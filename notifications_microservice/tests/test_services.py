from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.errors import ConflictError, NotFoundError, ValidationError
from app.services import NotificationService


@pytest.fixture
def repo():
    return MagicMock()


@pytest.fixture
def service(repo):
    return NotificationService(repository=repo)


def test_create_notification_rejects_invalid_usuario(service):
    with pytest.raises(ValidationError):
        service.create_notification(usuario_id=0, tipo="pedido", mensaje="Hola")


def test_create_notification_rejects_invalid_tipo(service):
    with pytest.raises(ValidationError):
        service.create_notification(usuario_id=1, tipo="no-valido", mensaje="Hola")


def test_create_notification_rejects_blank_mensaje(service):
    with pytest.raises(ValidationError):
        service.create_notification(usuario_id=1, tipo="pedido", mensaje="   ")


def test_create_notification_success(service, repo):
    repo.create.return_value = "notif"
    result = service.create_notification(usuario_id=1, tipo="PEDIDO", mensaje=" Hola ")
    assert result == "notif"
    repo.create.assert_called_once_with(usuario_id=1, tipo="pedido", mensaje="Hola")


def test_get_user_notifications_rejects_invalid_usuario(service):
    with pytest.raises(ValidationError):
        service.get_user_notifications(usuario_id=0)


def test_get_user_notifications_delegates_to_repo(service, repo):
    repo.list_by_user.return_value = ["a"]
    assert service.get_user_notifications(usuario_id=1) == ["a"]


def test_mark_as_read_not_found_raises(service, repo):
    repo.get_by_id.return_value = None
    with pytest.raises(NotFoundError):
        service.mark_as_read(notification_id=1)


def test_mark_as_read_already_read_raises_conflict(service, repo):
    repo.get_by_id.return_value = MagicMock(leida=True)
    with pytest.raises(ConflictError):
        service.mark_as_read(notification_id=1)


def test_mark_as_read_success(service, repo):
    repo.get_by_id.return_value = MagicMock(leida=False)
    repo.mark_as_read.return_value = "updated"
    assert service.mark_as_read(notification_id=1) == "updated"


def test_mark_as_read_race_condition_returns_not_found(service, repo):
    """Si el repo.get_by_id ve la notificacion pero mark_as_read no la
    encuentra (borrada entre medio), debe propagarse como NotFoundError."""
    repo.get_by_id.return_value = MagicMock(leida=False)
    repo.mark_as_read.return_value = None
    with pytest.raises(NotFoundError):
        service.mark_as_read(notification_id=1)
