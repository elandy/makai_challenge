import asyncio
import json
import logging
import os
from uuid import UUID

import aio_pika
from aio_pika.abc import AbstractIncomingMessage

from apps.worker.processor import process_job
from shared.db.session import AsyncSessionLocal
from apps.notifier.factory import build_notifier
import httpx

http_client = httpx.AsyncClient()

notifier = build_notifier()

logger = logging.getLogger(__name__)

RABBITMQ_URL = os.getenv(
    "RABBITMQ_URL",
    "amqp://guest:guest@localhost/",
)
QUEUE_NAME = "job-processing"

async def connect_with_retry(url: str):
    for i in range(20):
        try:
            return await aio_pika.connect_robust(url)
        except Exception as e:
            logger.warning(f"RabbitMQ not ready, retrying... ({i}) {e}")
            await asyncio.sleep(2)

    raise RuntimeError("Could not connect to RabbitMQ")

async def handle_message(message: AbstractIncomingMessage) -> None:
    async with message.process():
        try:
            payload = json.loads(message.body.decode())
            job_id = UUID(payload["job_id"])
            logger.info(f"Received job {job_id}")
            async with AsyncSessionLocal() as db:
                await process_job(db, job_id, notifier)
            logger.info(f"Successfully processed job {job_id}")
        except Exception:
            logger.exception("Worker failed processing message")
            raise


async def start_consumer() -> None:
    logger.info("Starting RabbitMQ consumer")
    connection = await connect_with_retry(RABBITMQ_URL)
    channel = await connection.channel()

    await channel.set_qos(prefetch_count=10)
    queue = await channel.declare_queue(
        QUEUE_NAME,
        durable=True,
    )

    await queue.consume(handle_message)
    logger.info("Consumer is waiting for messages")