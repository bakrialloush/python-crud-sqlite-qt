"""Table model for the ledger report."""

from __future__ import annotations

from collections.abc import Callable
from typing import ClassVar

from PyQt6.QtCore import Qt

from app.domain.views import LedgerLine
from app.ui.formatting import (
    format_credit,
    format_datetime,
    format_debit,
    format_decimal,
    transaction_text,
    transaction_type_label,
)
from app.ui.models.base_table_model import BaseTableModel

_DATE_COLUMN = 0
_TYPE_COLUMN = 1
_ACCOUNT_COLUMN = 2
_NOTES_COLUMN = 3
_DEBIT_COLUMN = 4
_CREDIT_COLUMN = 5
_BALANCE_COLUMN = 6

_RIGHT_ALIGNED: frozenset[int] = frozenset(
    {_DEBIT_COLUMN, _CREDIT_COLUMN, _BALANCE_COLUMN}
)

#: What the line the period opens on reads as, where a posting names the account
#: on its other side. It is a label rather than a domain value because naming the
#: report's first line is presentation, like placing a figure in a column.
_OPENING_LABEL = "Opening balance"


def _date(line: LedgerLine) -> str:
    """The posting's instant, blank on the opening line."""
    return "" if line.datetime is None else format_datetime(line.datetime)


def _type(line: LedgerLine) -> str:
    """The posting's kind, blank on the opening line."""
    if line.transaction_type is None:
        return ""
    return transaction_type_label(line.transaction_type)


def _account(line: LedgerLine) -> str:
    """The counterparty, or the opening label on the line that has none."""
    return _OPENING_LABEL if line.is_opening else line.counterparty


class LedgerTableModel(BaseTableModel[LedgerLine]):
    """Renders one account's ledger: a movement per line, and the balance after it.

    Each row carries one signed amount; which of the two columns it lands in is
    decided here, because it is a question about the report rather than about the
    posting — the same split the trial balance makes, from the same shared
    renderers. Left blank on the opening line, whose figure is a position rather
    than a movement: putting it in a column would make that column's total count
    it twice.
    """

    headers = ("Date", "Type", "Account", "Notes", "Debit", "Credit", "Balance")

    _RENDERERS: ClassVar[tuple[Callable[[LedgerLine], str], ...]] = (
        _date,
        _type,
        _account,
        lambda line: line.notes,
        lambda line: format_debit(line.amount),
        lambda line: format_credit(line.amount),
        lambda line: format_decimal(line.balance),
    )

    def display(self, item: LedgerLine, column: int) -> str:
        return self._RENDERERS[column](item)

    def alignment(self, column: int) -> Qt.AlignmentFlag:
        if column in _RIGHT_ALIGNED:
            return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        return super().alignment(column)

    def tooltip(self, item: LedgerLine, column: int) -> str | None:
        if column == _ACCOUNT_COLUMN and item.is_opening:
            return (
                "What the account held when the period began — everything "
                "posted to it before the from date."
            )
        if column == _BALANCE_COLUMN:
            return (
                "The account's position after this line. Debits are positive and "
                "credits negative, so a negative figure is a credit balance."
            )
        if column == _TYPE_COLUMN and item.transaction_type is not None:
            # The posting in words: the two figures behind this line are what the
            # transaction actually is, and the direction is the type's.
            words = transaction_text(item.transaction_type)
            return (
                f"{transaction_type_label(item.transaction_type)} of "
                f"{format_decimal(abs(item.amount))} posted "
                f"{words.preposition} {item.counterparty}."
            )
        if column == _NOTES_COLUMN and item.notes:
            return item.notes
        return None
