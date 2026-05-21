import asyncio

from apps.worker.consumer import start_consumer


async def main() -> None:
    await start_consumer()

    # Keep process alive forever
    await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())