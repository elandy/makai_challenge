import json
import logging
import os
from uuid import UUID

import aio_pika

logger = logging.getLogger(__name__)

RABBITMQ_URL = os.getenv(
    "RABBITMQ_URL",
    "amqp://guest:guest@localhost/",
)
QUEUE_NAME = "job-processing"


async def enqueue_job(job_id: UUID) -> None:
    logger.info(f"Enqueueing job {job_id}")

    connection = await aio_pika.connect_robust(RABBITMQ_URL)

    async with connection:
        channel = await connection.channel()

        await channel.declare_queue(
            QUEUE_NAME,
            durable=True,
        )

        message_body = json.dumps({
            "job_id": str(job_id),
        }).encode()

        message = aio_pika.Message(
            body=message_body,
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        )

        await channel.default_exchange.publish(
            message,
            routing_key=QUEUE_NAME,
        )

        logger.info(f"Successfully enqueued job {job_id}")