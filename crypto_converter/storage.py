import abc
from datetime import datetime
from decimal import Decimal

import databases
from pydantic import BaseModel


class Quote(BaseModel):
    symbol: str
    rate: Decimal
    dt: datetime


class Storage(abc.ABC):
    @abc.abstractmethod
    async def get(self, symbol: str, inverse_symbol: str, dt: datetime) -> Quote | None:
        """
        Get latest quote before timestamp for symbol.
        """
        pass

    @abc.abstractmethod
    async def save(self, quotes: list[Quote]) -> None:
        """
        Save quotes for timestamp.
        """
        pass

    @abc.abstractmethod
    async def cleanup(self, dt: datetime) -> None:
        """
        Remove quotes older than timestamp.
        """
        pass


class PostgreSQLStorage(Storage):
    def __init__(
        self, host: str, port: str, user: str, password: str, database: str
    ) -> None:
        self.db = databases.Database(
            f"postgresql://{user}:{password}@{host}:{port}/{database}"
        )

    async def _create_table(self) -> None:
        query = """
            CREATE TABLE IF NOT EXISTS quotes (
                timestamp TIMESTAMP NOT NULL,
                symbol VARCHAR(20) NOT NULL,
                quote DECIMAL NOT NULL,
                PRIMARY KEY (timestamp, symbol)
            )
        """
        await self.db.execute(query=query)

    async def connect(self) -> None:
        await self.db.connect()
        await self._create_table()

    async def disconnect(self) -> None:
        await self.db.disconnect()

    async def get(self, symbol: str, inverse_symbol: str, dt: datetime) -> Quote | None:
        query = """
            SELECT timestamp, symbol, quote
            FROM quotes
            WHERE (symbol = :symbol OR symbol = :inverse_symbol) AND
                timestamp <= :timestamp
            ORDER BY timestamp DESC
            LIMIT 1
        """
        row = await self.db.fetch_one(
            query=query,
            values={
                "symbol": symbol,
                "inverse_symbol": inverse_symbol,
                "timestamp": dt,
            },
        )
        return (
            Quote(symbol=row["symbol"], rate=Decimal(row["quote"]), dt=row["timestamp"])
            if row
            else None
        )

    async def save(self, quotes: list[Quote]) -> None:
        if not quotes:
            return

        query = "INSERT INTO quotes (timestamp, symbol, quote) VALUES "
        query += ", ".join(
            [f"(:timestamp, :symbol{i}, :quote{i})" for i in range(len(quotes))]
        )

        values: dict[str, datetime | str | Decimal] = {"timestamp": quotes[0].dt}
        for i, quote in enumerate(quotes):
            values[f"symbol{i}"] = quote.symbol
            values[f"quote{i}"] = quote.rate

        await self.db.execute(query=query, values=values)

    async def cleanup(self, dt: datetime) -> None:
        query = "DELETE FROM quotes WHERE timestamp < :timestamp"
        values = {"timestamp": dt}
        await self.db.execute(query=query, values=values)
