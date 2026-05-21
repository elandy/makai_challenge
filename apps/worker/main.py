import asyncio
import logging

from apps.worker.consumer import start_consumer


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )

    await start_consumer()

    # Keep process alive forever
    await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
