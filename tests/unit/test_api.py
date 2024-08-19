from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from crypto_converter.storage import Quote, Storage


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


@pytest.mark.asyncio
async def test_convert_quote_ok(client: TestClient, storage: Storage) -> None:
    await storage.save(
        [Quote(symbol="BTCUSDT", dt=datetime.now(), rate=Decimal("10000.000000000000"))]
    )

    response = client.get("/convert?from=BTC&to=USDT&amount=1")
    assert response.status_code == 200
    assert response.json() == {
        "amount": "10000.000000",
        "conversion_rate": "10000.000000000000",
    }


@pytest.mark.asyncio
async def test_convert_quote_not_found(client: TestClient, storage: Storage) -> None:
    response = client.get("/convert?from=BTC&to=USDT&amount=1")
    assert response.status_code == 404
    assert response.json() == {"detail": "Quote not found"}


@pytest.mark.asyncio
async def test_convert_quote_outdated(client: TestClient, storage: Storage) -> None:
    await storage.save(
        [
            Quote(
                symbol="BTCUSDT",
                dt=datetime.now() - timedelta(seconds=61),
                rate=Decimal("10000.000000000000"),
            )
        ]
    )

    response = client.get("/convert?from=BTC&to=USDT&amount=1")
    assert response.status_code == 404
    assert response.json() == {"detail": "Quote is outdated"}


@pytest.mark.asyncio
async def test_convert_quote_inversed_symbol(
    client: TestClient, storage: Storage
) -> None:
    await storage.save(
        [Quote(symbol="BTCUSDT", dt=datetime.now(), rate=Decimal("8000.000000000000"))]
    )

    response = client.get("/convert?from=USDT&to=BTC&amount=1")
    assert response.status_code == 200
    assert response.json() == {
        "amount": "0.000125",
        "conversion_rate": "8000.000000000000",
    }
