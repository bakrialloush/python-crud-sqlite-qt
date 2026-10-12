"""SQLite persistence for currencies."""

from __future__ import annotations

import sqlite3
from decimal import Decimal

from app.domain.currency import Currency
from app.domain.enums import RateMethod
from app.repositories.sqlite_repository import SqliteRepository


class SqliteCurrencyRepository(SqliteRepository[Currency]):
    """Reads and writes the ``currencies`` table."""

    table = "currencies"
    columns = ("name", "code", "rate", "method")

    def _to_entity(self, row: sqlite3.Row) -> Currency:
        return Currency(
            id=row["id"],
            name=row["name"],
            code=row["code"],
            # The column is TEXT precisely so this round trip is exact.
            rate=Decimal(row["rate"]),
            method=RateMethod(row["method"]),
        )

    def _to_parameters(self, entity: Currency) -> tuple[object, ...]:
        return (
            entity.name,
            entity.code,
            str(entity.rate),
            entity.method.value,
        )

    def exists_by_code(self, code: str, *, exclude_id: int | None = None) -> bool:
        """Whether another currency already uses ``code``.

        Compared with ``UPPER()`` to match ``idx_currencies_code``, so the check
        agrees with the constraint that ultimately enforces it.
        """
        sql = "SELECT 1 FROM currencies WHERE UPPER(code) = ?"
        parameters: list[object] = [code.strip().upper()]
        if exclude_id is not None:
            sql += " AND id <> ?"
            parameters.append(exclude_id)
        return bool(self._database.query(f"{sql} LIMIT 1", parameters))
