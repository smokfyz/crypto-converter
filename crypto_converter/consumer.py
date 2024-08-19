import abc
import asyncio
import json
import logging
from datetime import datetime, timedelta

import aiohttp
import websockets
from pydantic import BaseModel

from .storage import Quote, Storage
from .utils import quantize_decimal


BINANCE_API_ENDPOINT = "https://api.binance.com/api/v3/ticker/24hr"
BINANCE_WS_ENDPOINT = "wss://stream.binance.com:9443/ws/!ticker@arr"

RUN_TASKS_INTERVAL = 1


log = logging.getLogger(__name__)


class ConsumerConfig(BaseModel):
    save_period_seconds: int
    cleanup_period_seconds: int
    cleanup_older_than_seconds: int
    conversion_rate_precision: int


class Consumer(abc.ABC):
    def __init__(
        self,
        config: ConsumerConfig,
        storage: Storage,
        session: aiohttp.ClientSession,
        done: asyncio.Event,
    ) -> None:
        self.config = config
        self.storage = storage
        self.session = session
        self.done = done

        self.previous_consume_time = datetime.now() - timedelta(
            seconds=config.save_period_seconds
        )
        self.previous_cleanup_time = datetime.now() - timedelta(
            seconds=config.cleanup_period_seconds
        )

    @abc.abstractmethod
    async def consume(self) -> None:
        pass

    async def cleanup(self) -> None:
        now = datetime.now()

        if now - self.previous_cleanup_time < timedelta(
            seconds=self.config.cleanup_period_seconds
        ):
            return

        log.info("Cleanup started.")

        self.previous_cleanup_time = now
        await self.storage.cleanup(
            now - timedelta(seconds=self.config.cleanup_older_than_seconds)
        )

        log.info("Cleanup done.")

    async def run(self) -> None:
        log.info(
            f"Consumer started. Consume period: {self.config.save_period_seconds}s, "
            f"cleanup period: {self.config.cleanup_period_seconds}s, "
            f"cleanup older than: {self.config.cleanup_older_than_seconds}s, "
            f"conversion rate precision: {self.config.conversion_rate_precision}."
        )

        while not self.done.is_set():
            await asyncio.gather(self.consume(), self.cleanup())
            await asyncio.sleep(RUN_TASKS_INTERVAL)


class BinanceHTTPConsumer(Consumer):
    async def consume(self) -> None:
        now = datetime.now()

        if now - self.previous_consume_time < timedelta(
            seconds=self.config.save_period_seconds
        ):
            return

        log.info("Consuming started.")

        self.previous_consume_time = now

        response = await self.session.get(BINANCE_API_ENDPOINT)
        try:
            response.raise_for_status()
        except aiohttp.ClientResponseError as e:
            log.error(f"Failed to consume quotes: {e}")
            return

        quotes_raw = await response.json()
        quotes = [
            Quote(
                symbol=quote["symbol"],
                rate=quantize_decimal(
                    quote["lastPrice"], self.config.conversion_rate_precision
                ),
                dt=datetime.fromtimestamp(quote["closeTime"] / 1000),
            )
            for quote in quotes_raw
        ]

        log.info(f"Saving {len(quotes)} quotes.")

        await self.storage.save(quotes)

        log.info("Consuming done.")


class BinanceWSConsumer(Consumer):
    def __init__(
        self,
        config: ConsumerConfig,
        storage: Storage,
        session: aiohttp.ClientSession,
        done: asyncio.Event,
    ) -> None:
        super().__init__(config, storage, session, done)

        self.accumulated_quotes: dict[str, str] = {}
        self.last_timestamp = 0

        asyncio.create_task(self._consume_ws())

    async def _initialize_accumulated_quotes(self) -> None:
        response = await self.session.get(BINANCE_API_ENDPOINT)
        response.raise_for_status()

        quotes = await response.json()
        self.accumulated_quotes = {
            quote["symbol"]: quote["lastPrice"] for quote in quotes
        }
        self.last_timestamp = quotes[0]["closeTime"]

    async def _consume_ws(self) -> None:
        await self._initialize_accumulated_quotes()

        async with websockets.connect(BINANCE_WS_ENDPOINT) as websocket:
            async for message in websocket:
                quotes = json.loads(message)

                log.debug(f"Received message with {len(quotes)} quotes.")

                for quote in quotes:
                    self.accumulated_quotes[quote["s"]] = quote["c"]
                    self.last_timestamp = quote["E"]

                if self.done.is_set():
                    break

    async def consume(self) -> None:
        now = datetime.now()

        if now - self.previous_consume_time < timedelta(
            seconds=self.config.save_period_seconds
        ):
            return

        log.info("Consuming started.")

        self.previous_consume_time = now

        quotes = [
            Quote(
                symbol=symbol,
                rate=quantize_decimal(rate, self.config.conversion_rate_precision),
                dt=datetime.fromtimestamp(self.last_timestamp / 1000),
            )
            for symbol, rate in self.accumulated_quotes.items()
        ]

        log.info(f"Saving {len(quotes)} quotes.")

        await self.storage.save(quotes)

        log.info("Consuming done.")
