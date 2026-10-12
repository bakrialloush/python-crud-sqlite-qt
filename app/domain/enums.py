"""Enumerations shared by the domain, service and presentation layers."""

from __future__ import annotations

from decimal import Decimal
from enum import Enum


class RateMethod(str, Enum):
    """How a currency's rate combines with an amount.

    Subclassing ``str`` lets the value bind straight into SQLite and round-trip
    through ``RateMethod(value)`` without a lookup table. Always use ``.value``
    rather than ``str(member)``: since Python 3.11 the latter yields
    ``"RateMethod.MUL"`` for mixed-in enums.
    """

    MUL = "mul"
    DIV = "div"

    def apply(self, amount: Decimal, rate: Decimal) -> Decimal:
        """Combine ``amount`` and ``rate`` using this method's operator."""
        if self is RateMethod.DIV:
            return amount / rate
        return amount * rate

    @property
    def symbol(self) -> str:
        """The arithmetic sign, for tooltips and labels."""
        return "/" if self is RateMethod.DIV else "*"


class AccountType(str, Enum):
    """Account classification, following the accounting equation."""

    ASSET = "asset"
    LIABILITY = "liability"
    EQUITY = "equity"
    REVENUE = "revenue"
    EXPENSE = "expense"
