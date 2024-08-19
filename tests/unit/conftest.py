from datetime import datetime

import pytest
from fastapi import FastAPI

from crypto_converter.api import APIConfig, create_app
from crypto_converter.storage import Quote, Storage


class InMemoryStorage(Storage):
    def __init__(self) -> None:
        self.quotes: list[Quote] = []

    async def get(self, symbol: str, inverse_symbol: str, dt: datetime) -> Quote | None:
        for quote in self.quotes[::-1]:
            if (
                quote.symbol == symbol or quote.symbol == inverse_symbol
            ) and quote.dt < dt:
                return quote
        return None

    async def save(self, quotes: list[Quote]) -> None:
        self.quotes.extend(quotes)

    async def cleanup(self, dt: datetime) -> None:
        self.quotes = [quote for quote in self.quotes if quote.dt < dt]


@pytest.fixture
def storage() -> Storage:
    return InMemoryStorage()


@pytest.fixture
def app(storage: InMemoryStorage) -> FastAPI:
    return create_app(APIConfig(amount_precision=6, no_older_than_seconds=60), storage)
