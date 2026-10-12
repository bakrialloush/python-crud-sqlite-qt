"""Table model for the currency list.

The two class constants are parallel to :attr:`headers`: one renderer per
column, in the same order, so adding a column is a one-line change in each.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import ClassVar

from PyQt6.QtCore import Qt

from app.domain.currency import Currency
from app.ui.formatting import format_decimal, rate_method_label
from app.ui.models.base_table_model import BaseTableModel

_ID_COLUMN = 0
_RATE_COLUMN = 3

_RIGHT_ALIGNED: frozenset[int] = frozenset({_ID_COLUMN, _RATE_COLUMN})


class CurrencyTableModel(BaseTableModel[Currency]):
    """Renders currencies: id, name, code, rate and method."""

    headers = ("ID", "Name", "Code", "Rate", "Method")

    _RENDERERS: ClassVar[tuple[Callable[[Currency], str], ...]] = (
        lambda currency: "" if currency.id is None else str(currency.id),
        lambda currency: currency.name,
        lambda currency: currency.code,
        lambda currency: format_decimal(currency.rate),
        lambda currency: rate_method_label(currency.method),
    )

    def display(self, item: Currency, column: int) -> str:
        return self._RENDERERS[column](item)

    def alignment(self, column: int) -> Qt.AlignmentFlag:
        if column in _RIGHT_ALIGNED:
            return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        return super().alignment(column)

    def tooltip(self, item: Currency, column: int) -> str | None:
        if column == _RATE_COLUMN:
            return f"1 base unit = {format_decimal(item.rate)} {item.code}"
        return None
