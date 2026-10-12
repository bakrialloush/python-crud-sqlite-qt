"""Table model for the account list."""

from __future__ import annotations

from collections.abc import Callable
from typing import ClassVar

from PyQt6.QtCore import Qt

from app.domain.views import AccountView
from app.ui.formatting import account_type_label
from app.ui.models.base_table_model import BaseTableModel

_ID_COLUMN = 0
_CURRENCY_COLUMN = 3

_RIGHT_ALIGNED: frozenset[int] = frozenset({_ID_COLUMN})


class AccountTableModel(BaseTableModel[AccountView]):
    """Renders accounts: id, name, type and the currency they are held in."""

    headers = ("ID", "Name", "Type", "Currency")

    _RENDERERS: ClassVar[tuple[Callable[[AccountView], str], ...]] = (
        lambda account: str(account.id),
        lambda account: account.name,
        lambda account: account_type_label(account.type),
        lambda account: account.currency_code,
    )

    def display(self, item: AccountView, column: int) -> str:
        return self._RENDERERS[column](item)

    def alignment(self, column: int) -> Qt.AlignmentFlag:
        if column in _RIGHT_ALIGNED:
            return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        return super().alignment(column)

    def tooltip(self, item: AccountView, column: int) -> str | None:
        if column == _CURRENCY_COLUMN:
            return item.currency_name
        return None
