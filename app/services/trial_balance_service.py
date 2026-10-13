"""Trial balance use cases."""

from __future__ import annotations

from datetime import date
from datetime import datetime as DateTime
from datetime import time
from decimal import ROUND_HALF_UP, Decimal

from app.domain.currency import Currency
from app.domain.enums import AccountType
from app.domain.errors import ValidationError
from app.domain.views import AccountView, TrialBalance, TrialBalanceRow
from app.repositories.interfaces import (
    AccountRepository,
    CurrencyRepository,
    TransactionRepository,
)

#: The precision converted amounts are rounded to. The ``In Base`` column is the
#: one the report totals, so rounding each row is what keeps the footer equal to
#: the figures printed above it — at the cost of a residual when a rate does not
#: divide evenly, which the page shows rather than hides.
_CENTS = Decimal("0.01")

#: Account types in the order a trial balance lists them. Read off the enum's
#: own declaration, so a type added later cannot be left out of the sequence.
_TYPE_ORDER: dict[AccountType, int] = {
    account_type: index for index, account_type in enumerate(AccountType)
}


class TrialBalanceService:
    """Assembles the trial balance: what every account holds over a period.

    A report, not a use case that changes anything. An account's position is
    nothing but the sum of its splits, which the transaction repository already
    knows how to add up; what this adds is the two things that need the rest of
    the set — each account's own currency, and the base currency the figures are
    totalled in.
    """

    def __init__(
        self,
        accounts: AccountRepository,
        currencies: CurrencyRepository,
        transactions: TransactionRepository,
    ) -> None:
        self._accounts = accounts
        self._currencies = currencies
        self._transactions = transactions

    def period(self) -> tuple[date, date] | None:
        """The days the stored transactions span, or ``None`` when there are none.

        For prefilling the report's date fields, so it opens on the period the
        data covers instead of one the user has to discover.
        """
        bounds = self._transactions.date_bounds()
        if bounds is None:
            return None
        return (bounds[0].date(), bounds[1].date())

    def build(self, start: date, end: date) -> TrialBalance:
        """The trial balance for the period from ``start`` to ``end``, both ends.

        Raises:
            ValidationError: if the period runs backwards, or if no currency is
                marked as the base — without one there is nothing to total in.
        """
        if start > end:
            raise ValidationError(
                "The period's start date must not be after its end date.",
                field="start",
            )

        currencies = self._currencies.list_all()
        base = next((currency for currency in currencies if currency.is_base), None)
        if base is None:
            raise ValidationError(
                "No base currency is set, so the balances cannot be totalled."
            )
        by_id = {currency.id: currency for currency in currencies}

        # Every account, not only those that posted: an account with nothing in
        # the period is a zero figure the report is expected to show, and ``net``
        # supplies the zero for it.
        net = self._transactions.net_by_account(
            self._start_of(start), self._end_of(end)
        )

        rows = [
            self._row(account, net.get(account.id, Decimal(0)), by_id)
            for account in self._accounts.list_all_views()
        ]
        rows.sort(key=lambda row: (_TYPE_ORDER[row.account_type], row.account_name))

        return TrialBalance(
            rows=tuple(rows),
            base_code=base.code,
            total_in_base=sum((row.in_base for row in rows), Decimal(0)),
        )

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _row(
        account: AccountView, balance: Decimal, by_id: dict[int, Currency]
    ) -> TrialBalanceRow:
        """One account's row, its own figure and the same figure in base.

        The currency is looked up rather than defaulted: an account's currency
        is a foreign key that cannot be deleted while the account exists, so a
        miss here is a bug that should surface, not a case to paper over.
        """
        currency = by_id[account.currency_id]
        return TrialBalanceRow(
            account_id=account.id,
            account_name=account.name,
            account_type=account.type,
            currency_code=account.currency_code,
            balance=balance,
            in_base=currency.convert_to_base(balance).quantize(
                _CENTS, rounding=ROUND_HALF_UP
            ),
        )

    @staticmethod
    def _start_of(day: date) -> DateTime:
        """The first instant of ``day``."""
        return DateTime.combine(day, time.min)

    @staticmethod
    def _end_of(day: date) -> DateTime:
        """The last instant of ``day``, so the whole of it counts.

        Inclusive at both ends is the rule a period is read by, and this is
        where it is decided rather than in the repository or the widget.
        """
        return DateTime.combine(day, time.max)
