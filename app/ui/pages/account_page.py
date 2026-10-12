"""The Accounts tab."""

from __future__ import annotations

from PyQt6.QtWidgets import QDialog, QMessageBox, QWidget

from app.domain.account import Account
from app.domain.errors import AppError
from app.domain.views import AccountView
from app.services.account_service import AccountService
from app.ui.dialogs.account_dialog import AccountDialog
from app.ui.models.account_table_model import AccountTableModel
from app.ui.pages.crud_page import CrudPage

_NAME_COLUMN = 1


class AccountPage(CrudPage[AccountView]):
    """The accounts tab, displaying each account with its currency.

    Its row type is :class:`AccountView` rather than :class:`Account`, because
    the table shows the joined currency fields and resolving them per row would
    be an N+1.
    """

    def __init__(self, service: AccountService, parent: QWidget | None = None) -> None:
        super().__init__(
            service=service,
            model=AccountTableModel(),
            title="Accounts",
            entity_label="account",
            plural_label="accounts",
            name_column=_NAME_COLUMN,
            parent=parent,
        )
        self._accounts = service

    def _prompt(self, item: AccountView | None) -> bool:
        currencies = self._accounts.list_currencies()
        if not currencies:
            QMessageBox.information(
                self,
                "No currencies yet",
                "Create a currency first — an account has to be held in one.",
            )
            return False

        account: Account | None = None
        if item is not None:
            try:
                account = self._accounts.get(item.id)
            except AppError as error:
                self._report(error)
                return False

        dialog = AccountDialog(currencies, self._accounts.validate, account, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return False

        entered = dialog.account
        if entered is None:
            return False

        if item is None:
            return self._attempt(lambda: self._accounts.create(entered))
        return self._attempt(lambda: self._accounts.update(entered))

    def _remove(self, item: AccountView) -> None:
        self._accounts.delete(item.id)

    def _describe(self, item: AccountView) -> str:
        return f"{item.name} ({item.currency_code})"
