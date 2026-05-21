import httpx
from typing import Any
from .base import NotificationProvider


class WebhookNotifier(NotificationProvider):
    def __init__(self, client: httpx.AsyncClient):
        self.client = client

    async def send(self, *, user_id: str, event: str, payload: dict[str, Any]) -> None:
        url = payload.get("callback_url")
        if not url:
            return

        data = {key: value for key, value in payload.items() if key != "callback_url"}
        body = {
            "user_id": user_id,
            "event": event,  # "job.completed", "job.failed"
            "data": data,
        }

        await self.client.post(url, json=body, timeout=5)
