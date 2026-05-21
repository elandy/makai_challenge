from typing import Any, Iterable

from .providers.base import NotificationProvider


class Notifier:
    def __init__(self, providers: Iterable[NotificationProvider]):
        self.providers = list(providers)

    async def emit(self, *, user_id: str, event: str, payload: dict[str, Any]) -> None:
        for provider in self.providers:
            await provider.send(user_id=user_id, event=event, payload=payload)