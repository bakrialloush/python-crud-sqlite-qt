"""Ledger report use cases."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date
from decimal import Decimal

from app.domain.errors import NotFoundError, ValidationError
from app.domain.views import AccountView, Ledger, LedgerLine, LedgerPosting
from app.repositories.interfaces import AccountRepository, TransactionRepository
from app.services.period import end_of, start_of, transaction_period


class LedgerService:
    """Assembles one account's ledger: what it did over a period, line by line.

    A report, not a use case that changes anything. It reads the ledger the
    transactions wrote rather than keeping a balance of its own — the same
    stance the trial balance takes, one level of detail down: where that report
    shows each account's total, this shows the postings the total came from and
    the balance after each.

    Lighter than the trial balance in one way: it reports in the account's own
    currency, so nothing has to be converted and there is no base currency it
    could be missing.
    """

    def __init__(
        self,
        accounts: AccountRepository,
        transactions: TransactionRepository,
    ) -> None:
        self._accounts = accounts
        self._transactions = transactions

    def accounts(self) -> list[AccountView]:
        """The accounts the report can be read for, for the picker.

        Read fresh on every reload, so an account added, renamed or removed on
        the other tabs cannot leave the picker offering a stale list.
        """
        return self._accounts.list_all_views()

    def period(self) -> tuple[date, date] | None:
        """The days the stored transactions span, or ``None`` when there are none.

        For prefilling the report's date fields, so it opens on the period the
        data covers rather than one the user has to discover. The rule itself
        lives in :mod:`app.services.period`, shared with the trial balance.
        """
        return transaction_period(self._transactions)

    def build(self, account_id: int, start: date, end: date) -> Ledger:
        """The ledger of ``account_id`` for the period ``start`` to ``end``, both ends.

        The period decides which postings the report lists; it does not decide
        where the balance starts. Anything posted earlier is the opening balance
        the report opens on, so a period read on its own still says what the
        account held when it began.

        Raises:
            ValidationError: if the period runs backwards.
            NotFoundError: if there is no account with ``account_id``.
        """
        if start > end:
            raise ValidationError(
                "The period's start date must not be after its end date.",
                field="start",
            )

        account = self._account(account_id)
        opening = self._transactions.net_before(account_id, start_of(start))
        postings = self._transactions.list_postings(
            account_id, start_of(start), end_of(end)
        )

        return Ledger(
            account_id=account.id,
            account_name=account.name,
            account_type=account.type,
            currency_code=account.currency_code,
            # The opening line leads, always: the running balance has to start
            # somewhere and an account with no history in the period still has a
            # position, even when that position is zero.
            lines=(LedgerLine.opening(opening), *self._lines(postings, opening)),
        )

    # ------------------------------------------------------------------ helpers
    def _account(self, account_id: int) -> AccountView:
        """The account the report is for.

        Looked up rather than defaulted, and reported as a ``NotFoundError``: a
        miss means the caller asked about an account that is not there, which is
        a bug rather than a case to paper over with the first row to hand.
        """
        for account in self._accounts.list_all_views():
            if account.id == account_id:
                return account
        raise NotFoundError(f"No account with id {account_id}.")

    @staticmethod
    def _lines(postings: Iterable[LedgerPosting], opening: Decimal) -> list[LedgerLine]:
        """The postings as ledger lines, each carrying the balance after it.

        The running total is kept here, in ``Decimal``, rather than asked of the
        database once per line — the same reason the sums are: a stored TEXT
        amount added in SQL would come back a REAL. Carrying it forward from the
        opening balance also makes the last line's balance the closing one by
        construction, so the footer cannot disagree with the column above it.
        """
        balance = opening
        lines: list[LedgerLine] = []
        for posting in postings:
            balance += posting.amount
            lines.append(
                LedgerLine(
                    datetime=posting.datetime,
                    transaction_id=posting.transaction_id,
                    transaction_type=posting.type,
                    counterparty=posting.counterparty_name,
                    notes=posting.notes,
                    amount=posting.amount,
                    balance=balance,
                )
            )
        return lines
