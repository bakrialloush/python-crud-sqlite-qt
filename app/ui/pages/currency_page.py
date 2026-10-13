"""The Currencies tab."""

from __future__ import annotations

from PyQt6.QtWidgets import QDialog, QWidget

from app.domain.currency import Currency
from app.domain.errors import NotFoundError
from app.services.currency_service import CurrencyService
from app.ui.dialogs.currency_dialog import CurrencyDialog
from app.ui.models.currency_table_model import CurrencyTableModel
from app.ui.pages.crud_page import CrudPage

_NAME_COLUMN = 1


class CurrencyPage(CrudPage[Currency]):
    """Presentation only: every rule lives in :class:`CurrencyService`."""

    def __init__(self, service: CurrencyService, parent: QWidget | None = None) -> None:
        super().__init__(
            service=service,
            model=CurrencyTableModel(),
            title="Currencies",
            entity_label="currency",
            plural_label="currencies",
            name_column=_NAME_COLUMN,
            parent=parent,
        )
        self._currencies = service

    def _prompt(self, item: Currency | None) -> bool:
        dialog = CurrencyDialog(self._currencies.validate, item, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return False

        entered = dialog.currency
        if entered is None:
            return False

        if item is None:
            return self._attempt(lambda: self._currencies.create(entered))
        return self._attempt(lambda: self._currencies.update(entered))

    def _remove(self, item: Currency) -> None:
        currency_id = item.id
        if currency_id is None:
            raise NotFoundError("That currency has not been saved yet.")
        self._currencies.delete(currency_id)

    def _describe(self, item: Currency) -> str:
        return f"{item.code} — {item.name}"

    def _delete_refusal(self, item: Currency) -> str | None:
        if item.is_base:
            return f"{item.code} is the base currency and cannot be deleted."
        return None
