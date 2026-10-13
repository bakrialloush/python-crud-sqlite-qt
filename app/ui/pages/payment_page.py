"""The Payments tab."""

from __future__ import annotations

from PyQt6.QtWidgets import QDialog, QMessageBox, QWidget

from app.domain.enums import AccountType
from app.domain.errors import AppError
from app.domain.transaction import Transaction
from app.domain.views import TransactionView
from app.services.transaction_service import TransactionService
from app.ui.dialogs.payment_dialog import PaymentDialog
from app.ui.formatting import format_decimal
from app.ui.models.transaction_table_model import TransactionTableModel
from app.ui.pages.crud_page import CrudPage

#: Notes are what wants the leftover width; the columns before it are short and
#: sized to their contents.
_STRETCH_COLUMN = 5


class PaymentPage(CrudPage[TransactionView]):
    """The payments tab, listing each transaction with both of its accounts.

    Its row type is :class:`TransactionView` rather than :class:`Transaction`,
    because the table names the cash account and the account paid, and resolving
    those per row would be an N+1.
    """

    def __init__(
        self, service: TransactionService, parent: QWidget | None = None
    ) -> None:
        super().__init__(
            service=service,
            model=TransactionTableModel(),
            title="Payments",
            entity_label="payment",
            plural_label="payments",
            name_column=_STRETCH_COLUMN,
            parent=parent,
        )
        self._transactions = service

    def _prompt(self, item: TransactionView | None) -> bool:
        accounts = self._transactions.list_accounts()
        if not any(account.type is AccountType.ASSET for account in accounts):
            QMessageBox.information(
                self,
                "No cash account yet",
                "Create an asset account first — a payment has to come out of one.",
            )
            return False

        transaction: Transaction | None = None
        if item is not None:
            try:
                transaction = self._transactions.get(item.id)
            except AppError as error:
                self._report(error)
                return False

        dialog = PaymentDialog(
            accounts, self._transactions.validate, transaction, parent=self
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
            f"the payment of {format_decimal(item.amount)} "
            f"to {item.payment_account_name}"
        )
