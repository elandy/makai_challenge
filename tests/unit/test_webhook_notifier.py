from unittest.mock import AsyncMock

import pytest

from apps.notifier.providers.webhook import WebhookNotifier


@pytest.mark.asyncio
async def test_webhook_notifier_posts_to_callback_url():
    client = AsyncMock()
    notifier = WebhookNotifier(client)

    await notifier.send(
        user_id="user-1",
        event="job.completed",
        payload={
            "callback_url": "https://example.com/callback",
            "job_id": "job-1",
            "result": {"summary": "done"},
        },
    )

    client.post.assert_awaited_once_with(
        "https://example.com/callback",
        json={
            "user_id": "user-1",
            "event": "job.completed",
            "data": {
                "job_id": "job-1",
                "result": {"summary": "done"},
            },
        },
        timeout=5,
    )


@pytest.mark.asyncio
async def test_webhook_notifier_skips_payload_without_callback_url():
    client = AsyncMock()
    notifier = WebhookNotifier(client)

    await notifier.send(
        user_id="user-1",
        event="job.completed",
        payload={"job_id": "job-1"},
    )

    client.post.assert_not_called()
