"""SQLite persistence for accounts."""

from __future__ import annotations

import sqlite3

from app.domain.account import Account
from app.domain.enums import AccountType
from app.domain.views import AccountView
from app.repositories.sqlite_repository import SqliteRepository


class SqliteAccountRepository(SqliteRepository[Account]):
    """Reads and writes the ``accounts`` table."""

    table = "accounts"
    columns = ("name", "currency_id", "type")

    def _to_entity(self, row: sqlite3.Row) -> Account:
        return Account(
            id=row["id"],
            name=row["name"],
            currency_id=row["currency_id"],
            type=AccountType(row["type"]),
        )

    def _to_parameters(self, entity: Account) -> tuple[object, ...]:
        return (entity.name, entity.currency_id, entity.type.value)

    def list_all_views(self) -> list[AccountView]:
        """Accounts with their currency's code and name, in one query.

        A join rather than a lookup per row: the table displays the currency of
        every account, so resolving them lazily would be an N+1.
        """
        rows = self._database.query(
            """
            SELECT a.id          AS id,
                   a.name        AS name,
                   a.type        AS type,
                   a.currency_id AS currency_id,
                   c.code        AS currency_code,
                   c.name        AS currency_name
            FROM accounts AS a
            JOIN currencies AS c ON c.id = a.currency_id
            ORDER BY a.name COLLATE NOCASE, a.id
            """
        )
        return [
            AccountView(
                id=row["id"],
                name=row["name"],
                type=AccountType(row["type"]),
                currency_id=row["currency_id"],
                currency_code=row["currency_code"],
                currency_name=row["currency_name"],
            )
            for row in rows
        ]

    def count_by_currency(self, currency_id: int) -> int:
        """How many accounts use ``currency_id``."""
        rows = self._database.query(
            "SELECT COUNT(*) AS total FROM accounts WHERE currency_id = ?", (currency_id,)
        )
        return int(rows[0]["total"])
