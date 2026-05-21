from abc import ABC, abstractmethod
from typing import Any


class NotificationProvider(ABC):
    @abstractmethod
    async def send(self, *, user_id: str, event: str, payload: dict[str, Any]) -> None:
        ...