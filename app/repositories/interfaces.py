"""Ports describing what the service layer needs from persistence.

These Protocols deliberately import nothing that touches SQLite. That is what
lets ``app.services`` depend on an abstraction: the concrete repositories in
this package satisfy these shapes structurally, without the services ever
naming them.
"""

from __future__ import annotations

from typing import Protocol, TypeVar

from app.domain.account import Account
from app.domain.currency import Currency
from app.domain.split import Split
from app.domain.transaction import Transaction
from app.domain.views import AccountView, TransactionView

T = TypeVar("T")


class ReadRepository(Protocol[T]):
    """The read side of a repository."""

    def get(self, entity_id: int) -> T | None:
        """The entity with ``entity_id``, or ``None`` if there is no such row."""

    def list_all(self) -> list[T]:
        """Every entity, in a stable order."""


class WriteRepository(Protocol[T]):
    """The write side of a repository."""

    def add(self, entity: T) -> T:
        """Insert ``entity`` and return it with its assigned id."""

    def update(self, entity: T) -> T:
        """Overwrite the stored row matching ``entity.id``."""

    def delete(self, entity_id: int) -> bool:
        """Delete the row, reporting whether anything was removed."""


class CurrencyRepository(ReadRepository[Currency], WriteRepository[Currency], Protocol):
    """Currencies, plus the lookup the service rules need."""

    def exists_by_code(self, code: str, *, exclude_id: int | None = None) -> bool:
        """Whether another currency already uses ``code`` (case-insensitively)."""


class AccountRepository(ReadRepository[Account], WriteRepository[Account], Protocol):
    """Accounts, plus the queries the service rules need."""

    def list_all_views(self) -> list[AccountView]:
        """Accounts joined with their currency's display fields."""

    def count_by_currency(self, currency_id: int) -> int:
        """How many accounts use ``currency_id``. Zero means it is safe to delete."""


class TransactionRepository(
    ReadRepository[Transaction], WriteRepository[Transaction], Protocol
):
    """Transactions, plus the queries the service rules need.

    Writing a transaction is not a single insert: the two splits that make it a
    double-entry posting go with it, in the same database transaction. That is
    the implementation's business — ``add`` and ``update`` here mean "store this
    transaction and its postings", not "store this one row".
    """

    def list_all_views(self) -> list[TransactionView]:
        """Transactions joined with the names of the accounts they post to."""

    def list_splits(self, transaction_id: int) -> list[Split]:
        """The splits ``transaction_id`` posted, in a stable order."""

    def count_by_account(self, account_id: int) -> int:
        """How many transactions touch ``account_id``, on either side.

        Zero means the account has no ledger history and is safe to delete.
        """
