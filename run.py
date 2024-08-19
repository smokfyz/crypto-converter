import asyncio
import logging
import os
import signal
import typing
from contextlib import asynccontextmanager

import aiohttp
import click
import dotenv
import uvicorn
from fastapi import FastAPI

from crypto_converter.api import APIConfig, create_app
from crypto_converter.consumer import Consumer, ConsumerConfig
from crypto_converter.storage import PostgreSQLStorage


dotenv.load_dotenv()

# Common settings
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
POSTGRES_DB = os.getenv("POSTGRES_DB", "quotes")

# API settings
HOST = os.getenv("HOST", "localhost")
PORT = int(os.getenv("SERVER_PORT", 8000))
ENABLE_HOT_RELOAD = bool(os.getenv("ENABLE_HOT_RELOAD", 0))
NUM_WORKERS = int(os.getenv("NUM_WORKERS", 2))

AMOUNT_PRECISION = int(os.getenv("AMOUNT_PRECISION", 6))
NO_OLDER_THAN_SECONDS = int(os.getenv("NO_OLDER_THAN_SECONDS", 60))

# Consumer settings
CONVERSION_RATE_PRECISION = int(os.getenv("CONVERSION_RATE_PRECISION", 12))
SAVE_PERIOD_SECONDS = int(os.getenv("SAVE_PERIOD_SECONDS", 30))
CLEANUP_PERIOD_SECONDS = int(os.getenv("CLEANUP_PERIOD_SECONDS", 60 * 10))
CLEANUP_OLDER_THAN_SECONDS = int(
    os.getenv("CLEANUP_OLDER_THAN_SECONDS", 7 * 24 * 60 * 60)
)
CONSUMER_SUBSCRIBTION_TYPE = os.getenv("CONSUMER_SUBSCRIBTION_TYPE", "http")

logging_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

log_config = uvicorn.config.LOGGING_CONFIG
log_config["formatters"]["access"]["fmt"] = logging_format
log_config["formatters"]["default"]["fmt"] = logging_format

logging.basicConfig(format=logging_format, level=LOG_LEVEL)


def _create_app() -> FastAPI:
    config = APIConfig(
        amount_precision=AMOUNT_PRECISION, no_older_than_seconds=NO_OLDER_THAN_SECONDS
    )
    storage = PostgreSQLStorage(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        database=POSTGRES_DB,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> typing.AsyncGenerator[None, None]:
        try:
            await storage.connect()
            yield
        finally:
            await storage.disconnect()

    return create_app(config, storage, lifespan)


@click.group()
def cli() -> None:
    pass


@cli.command()
def api() -> None:
    uvicorn.run(
        "run:_create_app",
        factory=True,
        host=HOST,
        port=PORT,
        reload=ENABLE_HOT_RELOAD,
        workers=NUM_WORKERS,
        log_config=log_config,
        log_level=LOG_LEVEL.lower(),
    )


@cli.command()
def quotes_consumer() -> None:
    storage = PostgreSQLStorage(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        database=POSTGRES_DB,
    )
    config = ConsumerConfig(
        save_period_seconds=SAVE_PERIOD_SECONDS,
        cleanup_period_seconds=CLEANUP_PERIOD_SECONDS,
        cleanup_older_than_seconds=CLEANUP_OLDER_THAN_SECONDS,
        conversion_rate_precision=CONVERSION_RATE_PRECISION,
    )

    done = asyncio.Event()

    signal.signal(signal.SIGINT, lambda s, f: done.set())
    signal.signal(signal.SIGTERM, lambda s, f: done.set())

    async def run_consumer() -> None:
        await storage.connect()

        async with aiohttp.ClientSession() as session:
            match CONSUMER_SUBSCRIBTION_TYPE:
                case "http":
                    from crypto_converter.consumer import BinanceHTTPConsumer

                    consumer: Consumer = BinanceHTTPConsumer(
                        config, storage, session, done
                    )
                case "ws":
                    from crypto_converter.consumer import BinanceWSConsumer

                    consumer = BinanceWSConsumer(config, storage, session, done)
                case _:
                    raise ValueError(
                        "Unknown consumer subscription type "
                        f"{CONSUMER_SUBSCRIBTION_TYPE}"
                    )

            await consumer.run()

        await storage.disconnect()

    asyncio.run(run_consumer())


if __name__ == "__main__":
    cli()
