from __future__ import annotations

import logging

from common.domain.ports import WebPushExpiredError, WebPushPort
from common.exceptions import ConflictError, NotFoundError

from ..infrastructure.factories import NotificacionFactory
from .repositories import NotificacionRepository, PushSubscriptionRepository

logger = logging.getLogger(__name__)

_TIPO_TITULO = {
    "pedido": "CUCU · Pedido",
    "pago": "CUCU · Pago",
    "cerca": "CUCU",
    "sistema": "CUCU",
}


def _default_notificacion_repository() -> NotificacionRepository:
    from ..infrastructure.repositories_impl import DjangoNotificacionRepository

    return DjangoNotificacionRepository()


def _default_push_subscription_repo() -> PushSubscriptionRepository:
    from ..infrastructure.repositories_impl import DjangoPushSubscriptionRepository

    return DjangoPushSubscriptionRepository()


def _default_web_push_service() -> WebPushPort:
    from common.infrastructure.adapters import PywebpushWebPushAdapter

    return PywebpushWebPushAdapter()


class NotificacionService:
    def __init__(
        self,
        *,
        factory=NotificacionFactory,
        repository: NotificacionRepository | None = None,
        push_subscription_repo: PushSubscriptionRepository | None = None,
        web_push_service: WebPushPort | None = None,
    ):
        self._factory = factory
        self._repository = repository or _default_notificacion_repository()
        self._push_subscription_repo = push_subscription_repo or _default_push_subscription_repo()
        self._web_push_service = web_push_service or _default_web_push_service()

    def enviar(self, usuario, tipo, mensaje):
        notificacion = self._factory.crear(usuario=usuario, tipo=tipo, mensaje=mensaje)
        self._enviar_push(usuario=usuario, tipo=tipo, mensaje=mensaje)
        return notificacion

    def _enviar_push(self, *, usuario, tipo, mensaje) -> None:
        titulo = _TIPO_TITULO.get(tipo, "CUCU")
        for subscription in self._push_subscription_repo.list_for_user(usuario):
            try:
                self._web_push_service.enviar(subscription=subscription, titulo=titulo, mensaje=mensaje)
            except WebPushExpiredError:
                self._push_subscription_repo.delete_by_endpoint(subscription.endpoint)
            except Exception:
                # Un push perdido no debe romper el flujo principal (crear
                # la Notificacion en BD, aceptar un pedido, etc.).
                logger.warning("web_push_send_failed usuario=%s", getattr(usuario, "id", None), exc_info=True)

    def marcar_leida(self, notificacion_id):
        notificacion = self._repository.get_by_id(notificacion_id)
        if notificacion is None:
            raise NotFoundError("Notificación no encontrada")

        if notificacion.leida:
            raise ConflictError("La notificación ya fue leída")

        notificacion.leida = True
        self._repository.save_leida(notificacion)
        return notificacion

    def obtener_usuario(self, usuario):
        return self._repository.list_for_user(usuario)
