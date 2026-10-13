"""The transactions tabs: one instance for payments, one for receipts."""

from __future__ import annotations

from PyQt6.QtWidgets import QDialog, QMessageBox, QWidget

from app.domain.enums import AccountType, TransactionType
from app.domain.errors import AppError
from app.domain.transaction import Transaction
from app.domain.views import TransactionView
from app.services.transaction_service import TransactionService
from app.ui.dialogs.transaction_dialog import TransactionDialog
from app.ui.formatting import format_decimal, transaction_text
from app.ui.models.transaction_table_model import TransactionTableModel
from app.ui.pages.crud_page import CrudPage

#: Notes are what wants the leftover width; the columns before it are short and
#: sized to their contents.
_STRETCH_COLUMN = 5


class TransactionPage(CrudPage[TransactionView]):
    """A tab listing one transaction type, each row with both of its accounts.

    The Payments and Receipts tabs are two instances of this, differing only by
    the ``transaction_type`` they were built with — the same dialog and the same
    table model serve both, and the per-type wording comes from one place.

    Its row type is :class:`TransactionView` rather than :class:`Transaction`,
    because the table names the cash account and the counterparty, and resolving
    those per row would be an N+1.
    """

    def __init__(
        self,
        service: TransactionService,
        transaction_type: TransactionType,
        parent: QWidget | None = None,
    ) -> None:
        words = transaction_text(transaction_type)
        super().__init__(
            service=service,
            model=TransactionTableModel(),
            title=words.plural.capitalize(),
            entity_label=words.noun,
            plural_label=words.plural,
            name_column=_STRETCH_COLUMN,
            parent=parent,
        )
        self._transactions = service
        self._transaction_type = transaction_type
        self._words = words

    def _prompt(self, item: TransactionView | None) -> bool:
        accounts = self._transactions.list_accounts()
        if not any(account.type is AccountType.ASSET for account in accounts):
            QMessageBox.information(
                self, "No cash account yet", self._words.no_cash_message
            )
            return False

        transaction: Transaction | None = None
        if item is not None:
            try:
                transaction = self._transactions.get(item.id)
            except AppError as error:
                self._report(error)
                return False

        dialog = TransactionDialog(
            accounts,
            self._transaction_type,
            self._transactions.validate,
            transaction,
            parent=self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return False

        entered = dialog.transaction
        if entered is None:
            return False

        if item is None:
            return self._attempt(lambda: self._transactions.create(entered))
        return self._attempt(lambda: self._transactions.update(entered))

    def _remove(self, item: TransactionView) -> None:
        self._transactions.delete(item.id)

    def _describe(self, item: TransactionView) -> str:
        return (
            f"the {self._words.noun} of {format_decimal(item.amount)} "
            f"{self._words.preposition} {item.account_name}"
        )
