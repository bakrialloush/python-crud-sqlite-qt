"""Table model for the transaction list."""

from __future__ import annotations

from collections.abc import Callable
from typing import ClassVar

from PyQt6.QtCore import Qt

from app.domain.views import TransactionView
from app.ui.formatting import format_datetime, format_decimal, transaction_text
from app.ui.models.base_table_model import BaseTableModel

_ID_COLUMN = 0
_AMOUNT_COLUMN = 4
_NOTES_COLUMN = 5

_RIGHT_ALIGNED: frozenset[int] = frozenset({_ID_COLUMN, _AMOUNT_COLUMN})


class TransactionTableModel(BaseTableModel[TransactionView]):
    """Renders transactions: id, date, both accounts, amount and notes.

    The same model serves the Payments and Receipts tabs. The columns are the
    same either way — only the amount tooltip's wording turns on the row's type,
    because a payment moves money out and a receipt in.
    """

    headers = ("ID", "Date", "Cash account", "Account", "Amount", "Notes")

    _RENDERERS: ClassVar[tuple[Callable[[TransactionView], str], ...]] = (
        lambda transaction: str(transaction.id),
        lambda transaction: format_datetime(transaction.datetime),
        lambda transaction: transaction.cash_account_name,
        lambda transaction: transaction.account_name,
        lambda transaction: format_decimal(transaction.amount),
        lambda transaction: transaction.notes,
    )

    def display(self, item: TransactionView, column: int) -> str:
        return self._RENDERERS[column](item)

    def alignment(self, column: int) -> Qt.AlignmentFlag:
        if column in _RIGHT_ALIGNED:
            return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        return super().alignment(column)

    def tooltip(self, item: TransactionView, column: int) -> str | None:
        if column == _AMOUNT_COLUMN:
            # The posting in words, since the two rows behind this one number
            # are what the transaction actually is. The direction is the type's.
            words = transaction_text(item.type)
            return (
                f"{format_decimal(item.amount)} {words.flow} {item.cash_account_name}, "
                f"posted {words.preposition} {item.account_name}."
            )
        if column == _NOTES_COLUMN and item.notes:
            return item.notes
        return None
