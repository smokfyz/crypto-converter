import logging
from datetime import datetime, timedelta
from decimal import Decimal

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from starlette.types import Lifespan

from .storage import Storage
from .utils import quantize_decimal


log = logging.getLogger(__name__)


class APIConfig(BaseModel):
    amount_precision: int
    no_older_than_seconds: int


def create_app(
    config: APIConfig, storage: Storage, lifespan: Lifespan | None = None
) -> FastAPI:
    app = FastAPI(lifespan=lifespan)

    @app.get("/convert")
    async def convert(
        amount: Decimal,
        to: str,
        from_: str = Query(alias="from"),
        timestamp: int | None = None,
    ) -> dict:
        dt = datetime.now() if timestamp is None else datetime.fromtimestamp(timestamp)

        symbol, inverse_symbol = from_ + to, to + from_

        quote = await storage.get(symbol, inverse_symbol, dt)
        if quote is None:
            raise HTTPException(status_code=404, detail="Quote not found")

        if quote.dt < dt - timedelta(seconds=config.no_older_than_seconds):
            raise HTTPException(status_code=404, detail="Quote is outdated")

        amount = quantize_decimal(amount, config.amount_precision)
        if quote.symbol == symbol:
            converted_amount = amount * quote.rate
        else:
            converted_amount = amount / quote.rate

        return {
            "amount": quantize_decimal(converted_amount, config.amount_precision),
            "conversion_rate": quote.rate,
        }

    return app
