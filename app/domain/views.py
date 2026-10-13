"""Read models: projections assembled for display, never stored as tables."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime as DateTime
from decimal import Decimal

from app.domain.enums import AccountType, TransactionType


@dataclass(frozen=True)
class AccountView:
    """An account joined with the display fields of its currency.

    The accounts table needs the currency's code and name, so this carries them
    instead of making the presentation layer resolve the reference per row.
    """

    id: int
    name: str
    type: AccountType
    currency_id: int
    currency_code: str
    currency_name: str


@dataclass(frozen=True)
class TransactionView:
    """A transaction joined with the names of the two accounts it posts to.

    The payments table names both accounts, so this carries their names rather
    than making the presentation layer resolve each reference per row — the same
    reason :class:`AccountView` carries its currency.
    """

    id: int
    # ``datetime`` is imported as ``DateTime`` so the field does not shadow the
    # type it is annotated with, as in ``app.domain.transaction``.
    datetime: DateTime
    type: TransactionType
    amount: Decimal
    notes: str
    cash_account_id: int
    cash_account_name: str
    payment_account_id: int
    payment_account_name: str
