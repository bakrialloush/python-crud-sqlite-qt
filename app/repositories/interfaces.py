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
from app.domain.views import AccountView

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
