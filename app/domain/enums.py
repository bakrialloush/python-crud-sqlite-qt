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

    A payment takes money out of the cash account and posts it to the account
    being paid: the cash account is credited (a negative split) and the payment
    account debited (a positive one).

    The direction lives on the member rather than in the form or the entity so
    that the rule has one home: ``Transaction.splits`` reads the signs from
    here, and a second type added later cannot quietly disagree with the first.
    """

    PAYMENT = "payment"

    @property
    def cash_sign(self) -> int:
        """The sign of the cash account's split. Negative: a credit."""
        return -1

    @property
    def counterparty_sign(self) -> int:
        """The sign of the other account's split. Positive: a debit."""
        return 1
