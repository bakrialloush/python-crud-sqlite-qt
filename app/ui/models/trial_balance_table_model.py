"""Table model for the trial balance report."""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal
from typing import ClassVar

from PyQt6.QtCore import Qt

from app.domain.views import TrialBalanceRow
from app.ui.formatting import account_type_label, format_decimal
from app.ui.models.base_table_model import BaseTableModel

_DEBIT_COLUMN = 3
_CREDIT_COLUMN = 4
_IN_BASE_COLUMN = 5

_RIGHT_ALIGNED: frozenset[int] = frozenset(
    {_DEBIT_COLUMN, _CREDIT_COLUMN, _IN_BASE_COLUMN}
)


def _debit(balance: Decimal) -> str:
    """The balance when it is a debit one. A credit balance leaves this blank."""
    return format_decimal(balance) if balance > 0 else ""


def _credit(balance: Decimal) -> str:
    """The balance when it is a credit one, shown as a positive figure."""
    return format_decimal(-balance) if balance < 0 else ""


class TrialBalanceTableModel(BaseTableModel[TrialBalanceRow]):
    """Renders each account's balance in the Debit or the Credit column.

    The row carries one signed figure; which side of the trial balance it falls
    on is decided here, because it is a question about the report rather than
    about the account.
    """

    headers = ("Account", "Type", "Currency", "Debit", "Credit", "In Base")

    _RENDERERS: ClassVar[tuple[Callable[[TrialBalanceRow], str], ...]] = (
        lambda row: row.account_name,
        lambda row: account_type_label(row.account_type),
        lambda row: row.currency_code,
        lambda row: _debit(row.balance),
        lambda row: _credit(row.balance),
        lambda row: format_decimal(row.in_base),
    )

    def display(self, item: TrialBalanceRow, column: int) -> str:
        return self._RENDERERS[column](item)

    def alignment(self, column: int) -> Qt.AlignmentFlag:
        if column in _RIGHT_ALIGNED:
            return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        return super().alignment(column)

    def tooltip(self, item: TrialBalanceRow, column: int) -> str | None:
        if column == _IN_BASE_COLUMN:
            # The native figure is what the Debit or Credit column already
            # reads, so the tooltip is where the conversion is spelled out.
            return (
                f"{format_decimal(item.balance)} {item.currency_code} "
                f"converted into the base currency and rounded to cents."
            )
        return None
