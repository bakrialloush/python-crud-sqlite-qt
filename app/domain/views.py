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

    The transactions table names both accounts, so this carries their names
    rather than making the presentation layer resolve each reference per row —
    the same reason :class:`AccountView` carries its currency. ``account_*`` is
    the counterparty: the account paid for a payment, the account received from
    for a receipt.
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
    account_id: int
    account_name: str


@dataclass(frozen=True)
class LedgerPosting:
    """One split of one transaction, as the account it posted to reads it.

    The raw material of the ledger report: a repository read model, carrying the
    counterparty the split posted against. Which account that is follows from
    the transaction — it has exactly two, and the split belongs to one — so it is
    resolved by the query rather than looked up per row.
    """

    datetime: DateTime
    transaction_id: int
    type: TransactionType
    #: The account on the other side of the transaction, for the description.
    counterparty_id: int
    counterparty_name: str
    notes: str
    #: The signed split amount: debits positive, credits negative, always in the
    #: reported account's own currency.
    amount: Decimal


@dataclass(frozen=True)
class LedgerLine:
    """One line of an account's ledger: a posting, or the opening balance.

    A ledger reads as a list of movements with a balance after each, and its
    first line is not a movement at all — it is the position the account carried
    into the period. Modelling that as a line rather than a field beside the
    list is what lets the report render as one sequence: the running balance
    stays a property of the line above it, and the table model keeps the plain
    "one item per row" shape it has everywhere else.
    """

    #: The instant the posting is dated. ``None`` on the opening line, which is
    #: dated "before the period" rather than at any one time.
    datetime: DateTime | None
    #: ``None`` on the opening line, which no transaction produced.
    transaction_id: int | None
    #: ``None`` on the opening line, which has no type to describe it.
    transaction_type: TransactionType | None
    #: The account on the other side. Empty on the opening line.
    counterparty: str
    notes: str
    #: The signed movement: debits positive, credits negative. Zero on the
    #: opening line, which is a position rather than a movement — which is also
    #: why it leaves the report's Debit and Credit columns blank, so those two
    #: columns sum to the period's movement and nothing else.
    amount: Decimal
    #: The account's position after this line.
    balance: Decimal

    @property
    def is_opening(self) -> bool:
        """Whether this is the opening line rather than a posting.

        Derived from the missing transaction rather than stored as a flag, so
        the two cannot disagree: an opening line is exactly one no transaction
        produced. :meth:`opening` is the only place those fields are left unset.
        """
        return self.transaction_id is None

    @classmethod
    def opening(cls, balance: Decimal) -> "LedgerLine":
        """The line a period opens on: the position carried into it."""
        return cls(
            datetime=None,
            transaction_id=None,
            transaction_type=None,
            counterparty="",
            notes="",
            amount=Decimal(0),
            balance=balance,
        )


@dataclass(frozen=True)
class Ledger:
    """One account's ledger over one period.

    ``lines`` always begins with the opening line and is therefore never empty,
    even for an account that posted nothing: a report whose Balance column
    started from nowhere would be unreadable.
    """

    account_id: int
    account_name: str
    account_type: AccountType
    currency_code: str
    lines: tuple[LedgerLine, ...]

    @property
    def opening_balance(self) -> Decimal:
        """The position the period opens on — the first line's balance.

        Read off the line rather than carried beside it, so the figure the
        header states and the figure the first row shows are one value.
        """
        return self.lines[0].balance

    @property
    def closing_balance(self) -> Decimal:
        """The position the period closes on — the last line's balance.

        The footer shows this, so it equals the last row printed by
        construction rather than by a second addition that could drift from it.
        """
        return self.lines[-1].balance


@dataclass(frozen=True)
class TrialBalanceRow:
    """One account's position over a period, in its own currency and in base.

    ``balance`` is signed the way the ledger stores it — debits positive,
    credits negative — so a positive figure is a debit balance. Which column of
    the report it lands in follows from that sign, and stays out of this model:
    placing a balance is presentation, not a fact about the account.
    """

    account_id: int
    account_name: str
    account_type: AccountType
    currency_code: str
    balance: Decimal
    #: ``balance`` converted into the base currency, rounded to cents.
    in_base: Decimal


@dataclass(frozen=True)
class TrialBalance:
    """A whole trial balance: one row per account, over one period."""

    rows: tuple[TrialBalanceRow, ...]
    #: The currency each row's ``in_base`` is expressed in, for the column header.
    base_code: str
    #: The sum of the rows' ``in_base``. Zero means the report balances.
    total_in_base: Decimal
