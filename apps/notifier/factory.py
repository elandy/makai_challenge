import httpx

from apps.notifier.dispatcher import Notifier
from apps.notifier.providers.webhook import WebhookNotifier


def build_notifier() -> Notifier:
    http_client = httpx.AsyncClient()

    providers = []

    # for now, we only have webhook notification. If we implement more this could come from env/config
    providers.append(WebhookNotifier(http_client))

    return Notifier(providers=providers)