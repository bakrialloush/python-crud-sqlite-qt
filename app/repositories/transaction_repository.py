"""SQLite persistence for transactions and the splits they post."""

from __future__ import annotations

import sqlite3
from datetime import datetime as DateTime
from decimal import Decimal

from app.domain.enums import TransactionType
from app.domain.split import Split
from app.domain.transaction import Transaction
from app.domain.views import TransactionView
from app.repositories.sqlite_repository import SqliteRepository

#: The stored form of a timestamp. SQLite has no date type; this is the ISO 8601
#: shape that both sorts correctly as text and parses back with
#: ``datetime.strptime``. To the minute, not the second: the form offers minutes,
#: so storing seconds would let an edit silently nudge a timestamp it displayed
#: rounded. ``app.ui.formatting`` renders display timestamps in this same shape
#: and has to keep agreeing with it.
DATETIME_FORMAT = "%Y-%m-%d %H:%M"


class SqliteTransactionRepository(SqliteRepository[Transaction]):
    """Reads and writes the ``transactions`` table and its splits.

    A transaction is one row here and two rows in ``splits``. The rows are
    written together by :meth:`_write_owned_rows`, which the generic base calls
    inside the transaction it already opened — so the posting is all-or-nothing
    without this class managing a transaction boundary of its own.
    """

    table = "transactions"
    columns = (
        "datetime",
        "type",
        "cash_account_id",
        "payment_account_id",
        "amount",
        "notes",
    )

    def _to_entity(self, row: sqlite3.Row) -> Transaction:
        return Transaction(
            id=row["id"],
            datetime=DateTime.strptime(row["datetime"], DATETIME_FORMAT),
            type=TransactionType(row["type"]),
            cash_account_id=row["cash_account_id"],
            payment_account_id=row["payment_account_id"],
            # The column is TEXT precisely so this round trip is exact.
            amount=Decimal(row["amount"]),
            notes=row["notes"],
        )

    def _to_parameters(self, entity: Transaction) -> tuple[object, ...]:
        return (
            entity.datetime.strftime(DATETIME_FORMAT),
            entity.type.value,
            entity.cash_account_id,
            entity.payment_account_id,
            str(entity.amount),
            entity.notes,
        )

    def _write_owned_rows(self, cursor: sqlite3.Cursor, entity: Transaction) -> None:
        """Replace the transaction's splits with the two it posts.

        Clearing first makes this correct for an update as well as an insert —
        the base calls the one hook for both — and leaves the pair always
        describing the transaction as it now reads, rather than as it did.

        The amounts come from :meth:`Transaction.splits`, so the signs are
        decided in the domain and never re-derived here.
        """
        cursor.execute("DELETE FROM splits WHERE transaction_id = ?", (entity.id,))
        cursor.executemany(
            """
            INSERT INTO splits (transaction_id, account_id, amount)
            VALUES (?, ?, ?)
            """,
            [
                (entity.id, split.account_id, str(split.amount))
                for split in entity.splits()
            ],
        )

    def list_all_views(self) -> list[TransactionView]:
        """Transactions with the names of both accounts, in one query.

        Two joins rather than a lookup per row: the table names both accounts of
        every payment, so resolving them lazily would be an N+1.

        Both joins are inner joins, and both foreign keys are NOT NULL with no
        cascade, so an account named here cannot be missing — an account that a
        payment used cannot be deleted at all.
        """
        rows = self._database.query(
            """
            SELECT t.id                 AS id,
                   t.datetime           AS datetime,
                   t.type               AS type,
                   t.amount             AS amount,
                   t.notes              AS notes,
                   t.cash_account_id    AS cash_account_id,
                   cash.name            AS cash_account_name,
                   t.payment_account_id AS payment_account_id,
                   paid.name            AS payment_account_name
            FROM transactions AS t
            JOIN accounts AS cash ON cash.id = t.cash_account_id
            JOIN accounts AS paid ON paid.id = t.payment_account_id
            ORDER BY t.datetime DESC, t.id DESC
            """
        )
        return [
            TransactionView(
                id=row["id"],
                datetime=DateTime.strptime(row["datetime"], DATETIME_FORMAT),
                type=TransactionType(row["type"]),
                amount=Decimal(row["amount"]),
                notes=row["notes"],
                cash_account_id=row["cash_account_id"],
                cash_account_name=row["cash_account_name"],
                payment_account_id=row["payment_account_id"],
                payment_account_name=row["payment_account_name"],
            )
            for row in rows
        ]

    def list_splits(self, transaction_id: int) -> list[Split]:
        """The splits ``transaction_id`` posted, debits first.

        The read side of the posting. Nothing in the UI needs it yet — balances,
        which will, are a later change — but it is what makes the stored pair
        inspectable rather than write-only.
        """
        rows = self._database.query(
            """
            SELECT id, transaction_id, account_id, amount
            FROM splits
            WHERE transaction_id = ?
            ORDER BY amount < 0, id
            """,
            (transaction_id,),
        )
        return [
            Split(
                id=row["id"],
                transaction_id=row["transaction_id"],
                account_id=row["account_id"],
                amount=Decimal(row["amount"]),
            )
            for row in rows
        ]

    def count_by_account(self, account_id: int) -> int:
        """How many transactions touch ``account_id``, on either side.

        Counting transactions rather than splits because a split's account is
        always one of the transaction's own two, so the two counts agree — and
        the caller wants to say "used by N payments", not "used by N lines".
        """
        rows = self._database.query(
            """
            SELECT COUNT(*) AS total
            FROM transactions
            WHERE cash_account_id = ? OR payment_account_id = ?
            """,
            (account_id, account_id),
        )
        return int(rows[0]["total"])
