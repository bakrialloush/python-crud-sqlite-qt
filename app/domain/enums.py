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
    def inverse(self) -> RateMethod:
        """The method that undoes this one, converting an amount back again.

        :meth:`apply` works in the direction the rate was quoted in. The way
        back is the same rate with the opposite operator: dividing by a rate
        undoes multiplying by it, and the other way round.
        """
        return RateMethod.DIV if self is RateMethod.MUL else RateMethod.MUL

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


class TransactionType(str, Enum):
    """How a transaction moves money, and which side of it is the debit.

    A **payment** takes money out of the cash account: the cash account is
    credited (a negative split) and the counterparty debited (a positive one).
    A **receipt** is its mirror image — money in, so the cash account is debited
    and the counterparty credited.

    The direction lives on the member rather than in the form or the entity so
    that the rule has one home: ``Transaction.splits`` reads the signs from
    here, and a type added later cannot quietly disagree with the others. Each
    member carries its own cash sign, so a new one states its direction instead
    of inheriting whichever way the code happens to default.
    """

    def __new__(cls, value: str, cash_sign: int) -> "TransactionType":
        # The mixin keeps the member a ``str`` worth ``value``, so it still binds
        # straight into SQLite and round-trips through ``TransactionType(value)``;
        # the extra field travels beside it without becoming the stored value.
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj._cash_sign = cash_sign
        return obj

    PAYMENT = ("payment", -1)
    RECEIPT = ("receipt", 1)

    @property
    def cash_sign(self) -> int:
        """The sign of the cash account's split: negative out, positive in."""
        return self._cash_sign

    @property
    def counterparty_sign(self) -> int:
        """The sign of the other account's split — always opposite the cash one.

        Derived rather than stored: two postings that do not cancel would not be
        a double-entry transaction, so the invariant holds by construction.
        """
        return -self._cash_sign
