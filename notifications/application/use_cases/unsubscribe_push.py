from __future__ import annotations

from ...domain.repositories import PushSubscriptionRepository


def _default_push_subscription_repo() -> PushSubscriptionRepository:
    from ...infrastructure.repositories_impl import DjangoPushSubscriptionRepository

    return DjangoPushSubscriptionRepository()


class UnsubscribePushUseCase:
    def __init__(self, *, repository: PushSubscriptionRepository | None = None):
        self._repository = repository or _default_push_subscription_repo()

    def execute(self, *, endpoint: str) -> None:
        self._repository.delete_by_endpoint(endpoint)
