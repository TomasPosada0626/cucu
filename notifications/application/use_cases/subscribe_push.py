from __future__ import annotations

from ...domain.repositories import PushSubscriptionRepository


def _default_push_subscription_repo() -> PushSubscriptionRepository:
    from ...infrastructure.repositories_impl import DjangoPushSubscriptionRepository

    return DjangoPushSubscriptionRepository()


class SubscribePushUseCase:
    def __init__(self, *, repository: PushSubscriptionRepository | None = None):
        self._repository = repository or _default_push_subscription_repo()

    def execute(self, *, usuario, endpoint: str, p256dh: str, auth: str):
        return self._repository.create_or_update(usuario=usuario, endpoint=endpoint, p256dh=p256dh, auth=auth)
