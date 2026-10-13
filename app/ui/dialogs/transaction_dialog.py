"""Create and edit form for a transaction."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import replace
from decimal import Decimal

from PyQt6.QtCore import QDateTime
from PyQt6.QtWidgets import (
    QComboBox,
    QDateTimeEdit,
    QDialog,
    QFormLayout,
    QLineEdit,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.domain.enums import AccountType, TransactionType
from app.domain.errors import ValidationError
from app.domain.transaction import Transaction
from app.domain.validation import parse_decimal
from app.domain.views import AccountView
from app.ui.dialogs.form_support import (
    DIALOG_MINIMUM_WIDTH,
    build_button_box,
    build_form_layout,
    report_validation_error,
)
from app.ui.formatting import DATETIME_QT_FORMAT, format_decimal, transaction_text

#: Raised by the service to reject a transaction; called before the dialog closes.
TransactionValidator = Callable[[Transaction], None]


class TransactionDialog(QDialog):
    """One form for both creating and editing, for either direction of money.

    ``transaction_type`` fixes which way the transaction posts — a payment's
    dialog only ever writes payments, a receipt's only receipts — and supplies
    the wording, since the form is otherwise identical either way. ``transaction``
    selects the create or edit mode, exactly as ``account`` does for
    :class:`~app.ui.dialogs.account_dialog.AccountDialog`. The caller supplies
    the accounts and is responsible for at least one of them being an asset —
    the page checks before opening this, so the currency picker always has an
    entry and the cash picker is never empty.

    The form narrows from the top down. The currency picker offers the
    currencies holding an asset account; the cash picker offers that currency's
    assets; the account picker offers everything else in it, excluding the cash
    account itself. That is convenience rather than the rule:
    ``TransactionService.validate`` checks each again, so a stale or bypassed
    picker still cannot store a transaction that breaks any of them.
    """

    def __init__(
        self,
        accounts: Sequence[AccountView],
        transaction_type: TransactionType,
        validator: TransactionValidator,
        transaction: Transaction | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._accounts = tuple(accounts)
        self._transaction_type = transaction_type
        self._words = transaction_text(transaction_type)
        self._validator = validator
        self._original = transaction
        self._result: Transaction | None = None
        # Set while the form fills itself in, so the combo signals that fire
        # along the way do not rebuild a picker that is still being populated.
        self._loading = True

        mode = "Edit" if transaction is not None else "New"
        self.setWindowTitle(f"{mode} {self._words.noun}")
        self.setModal(True)
        self.setMinimumWidth(DIALOG_MINIMUM_WIDTH)

        form = self._build_fields()
        self._populate()

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(build_button_box(self))

        self._loading = False
        # After the guard is lifted, so the pickers fill once, already filtered
        # by the currency the form settled on — the cash accounts first, then
        # what that cash account settles on the other side.
        self._refill_cash_options()

    @property
    def transaction(self) -> Transaction | None:
        """The validated transaction, or ``None`` if the dialog was not accepted."""
        return self._result

    def accept(self) -> None:
        """Close only when the transaction is valid; otherwise keep the form open."""
        try:
            transaction = self._build_transaction()
            self._validator(transaction)
        except ValidationError as error:
            report_validation_error(self, error, self._field_widgets())
            return
        self._result = transaction
        super().accept()

    # ---------------------------------------------------------------- assembly
    def _build_fields(self) -> QFormLayout:
        # The moment is offered rather than assumed: a transaction entered today
        # for one from last week belongs on the day it happened, and the default
        # of "now" costs nothing when that is right.
        self._datetime_edit = QDateTimeEdit()
        self._datetime_edit.setCalendarPopup(True)
        self._datetime_edit.setDisplayFormat(DATETIME_QT_FORMAT)

        # A plain line edit for the same reason the rate uses one: a spin box
        # would route the amount through a C double and undo the Decimal.
        self._amount_edit = QLineEdit()
        self._amount_edit.setPlaceholderText("0.00")

        # The currency narrows both pickers below to the accounts held in it: a
        # transaction moves money rather than converting it, so the two accounts
        # it posts to are always held in one currency. Choosing it first is what
        # lets the cash picker offer that currency's assets instead of every
        # currency's.
        self._currency_combo = QComboBox()
        for currency_id, label in self._currency_options().items():
            self._currency_combo.addItem(label, currency_id)

        # Both filled by _refill_cash_options, which knows the chosen currency.
        self._cash_combo = QComboBox()
        self._account_combo = QComboBox()

        self._notes_edit = QPlainTextEdit()
        self._notes_edit.setPlaceholderText(self._words.notes_placeholder)
        self._notes_edit.setTabChangesFocus(True)
        self._notes_edit.setFixedHeight(self._notes_edit.fontMetrics().lineSpacing() * 3)

        self._currency_combo.currentIndexChanged.connect(self._on_currency_changed)
        self._cash_combo.currentIndexChanged.connect(self._on_cash_changed)

        form = build_form_layout()
        form.addRow("Date", self._datetime_edit)
        form.addRow("Amount", self._amount_edit)
        form.addRow("Currency", self._currency_combo)
        form.addRow("Cash account", self._cash_combo)
        # "Paid to" for a payment, "Received from" for a receipt — the only row
        # whose meaning turns on the direction the money travels.
        form.addRow(self._words.counterparty_label, self._account_combo)
        form.addRow("Notes", self._notes_edit)
        return form

    def _populate(self) -> None:
        if self._original is None:
            self._datetime_edit.setDateTime(QDateTime.currentDateTime())
            return
        self._datetime_edit.setDateTime(QDateTime(self._original.datetime))
        self._amount_edit.setText(format_decimal(self._original.amount))
        self._notes_edit.setPlainText(self._original.notes)
        # The currency before the accounts, because the pickers below cannot be
        # filled until the form knows which currency it is working in. Which
        # cash account to select is settled by _refill_cash_options, from the
        # account being edited rather than set here.
        self._select_currency(self._original_currency_id())

    # ------------------------------------------------------------- picker logic
    def _on_currency_changed(self, *_: object) -> None:
        if not self._loading:
            self._refill_cash_options()

    def _on_cash_changed(self, *_: object) -> None:
        if not self._loading:
            self._refill_account_options()

    def _refill_cash_options(self) -> None:
        """Refill the cash picker with the assets held in the chosen currency.

        Only assets, because every transaction posts through one — money out of
        it for a payment, in for a receipt — and only the chosen currency's,
        because the counterparty account is held in the same one.
        """
        preferred = self._preferred_cash_id()
        currency_id = self._selected_currency_id()

        # Held while the list is rebuilt, so the signals the rebuild fires do
        # not refill the account picker against a cash list that is only half
        # built; it is refilled once below, against what this settles on.
        was_loading = self._loading
        self._loading = True
        try:
            self._cash_combo.clear()
            if currency_id is not None:
                for account in self._accounts:
                    if (
                        account.type is AccountType.ASSET
                        and account.currency_id == currency_id
                    ):
                        self._cash_combo.addItem(account.name, account)
            self._select_account(self._cash_combo, preferred)
        finally:
            self._loading = was_loading
        self._refill_account_options()

    def _refill_account_options(self) -> None:
        """Refill the account picker with the accounts the cash account may post to.

        Only accounts held in the same currency, because a transaction moves
        money rather than converting it, and never the cash account itself,
        because debiting and crediting one account posts nothing.
        """
        preferred = self._preferred_account_id()
        cash = self._cash_combo.currentData()

        self._account_combo.clear()
        if not isinstance(cash, AccountView):
            return

        for account in self._accounts:
            if account.currency_id == cash.currency_id and account.id != cash.id:
                self._account_combo.addItem(account.name, account)
        self._select_account(self._account_combo, preferred)

    def _preferred_cash_id(self) -> int | None:
        """Which cash account to keep selected across a rebuild.

        Whatever the form already holds, or when it holds nothing — the first
        fill, or a change of currency that dropped it — the account being
        edited. An edit therefore opens on the row's own account rather than on
        whichever of the currency's assets happens to be first.
        """
        selected = self._selected_account_id(self._cash_combo)
        if selected is not None:
            return selected
        if self._original is not None:
            return self._original.cash_account_id
        return None

    def _preferred_account_id(self) -> int | None:
        """Which counterparty account to keep selected across a rebuild.

        Whatever the form already holds, or when it holds nothing — the first
        fill, or a cash account whose currency dropped it — the account being
        edited. An edit therefore opens on the row's own account rather than on
        whichever happens to be first.
        """
        selected = self._selected_account_id(self._account_combo)
        if selected is not None:
            return selected
        if self._original is not None:
            return self._original.account_id
        return None

    # ------------------------------------------------------------------ helpers
    def _currency_options(self) -> dict[int, str]:
        """The currencies a transaction can be made in, as id to display label.

        Only currencies holding an asset account: every transaction posts
        through one, so a currency with none could never fill the cash picker.
        Built from the accounts, which are the only currency data the caller
        supplies, and keyed by id so each currency appears once, where its first
        account does.
        """
        options: dict[int, str] = {}
        for account in self._accounts:
            if account.type is AccountType.ASSET:
                options.setdefault(
                    account.currency_id,
                    f"{account.currency_code} — {account.currency_name}",
                )
        return options

    def _original_currency_id(self) -> int | None:
        """The currency the transaction being edited was made in.

        Read from its cash account rather than stored on the transaction, which
        holds only the two account ids — the cash account being the one that
        carries the currency a transaction is made in.
        """
        if self._original is None:
            return None
        for account in self._accounts:
            if account.id == self._original.cash_account_id:
                return account.currency_id
        return None

    def _select_currency(self, currency_id: int | None) -> None:
        """Select the entry for ``currency_id``, when it is still on offer."""
        if currency_id is None:
            return
        index = self._currency_combo.findData(currency_id)
        if index != -1:
            self._currency_combo.setCurrentIndex(index)

    def _selected_currency_id(self) -> int | None:
        data = self._currency_combo.currentData()
        return data if isinstance(data, int) else None

    @staticmethod
    def _select_account(combo: QComboBox, account_id: int | None) -> None:
        """Select the entry for ``account_id``, when it is still on offer."""
        if account_id is None:
            return
        for index in range(combo.count()):
            data = combo.itemData(index)
            if isinstance(data, AccountView) and data.id == account_id:
                combo.setCurrentIndex(index)
                return

    @staticmethod
    def _selected_account_id(combo: QComboBox) -> int | None:
        data = combo.currentData()
        return data.id if isinstance(data, AccountView) else None

    def _build_transaction(self) -> Transaction:
        """Build a transaction from the form.

        Raises:
            ValidationError: if the amount cannot be parsed, or a picker is
                empty — which happens when the accounts were emptied from under
                the form.
        """
        amount: Decimal = parse_decimal(self._amount_edit.text(), field="amount")

        cash = self._cash_combo.currentData()
        if not isinstance(cash, AccountView):
            raise ValidationError(
                "A cash account must be selected.", field="cash_account_id"
            )
        counterparty = self._account_combo.currentData()
        if not isinstance(counterparty, AccountView):
            raise ValidationError(
                "The other account must be selected.", field="account_id"
            )

        values = {
            "datetime": self._datetime_edit.dateTime().toPyDateTime(),
            # Not a field on the form: the direction follows from the type this
            # dialog was opened for, not from anything the user could get wrong.
            "type": self._transaction_type,
            "cash_account_id": cash.id,
            "account_id": counterparty.id,
            "amount": amount,
            "notes": self._notes_edit.toPlainText(),
        }
        if self._original is None:
            return Transaction(**values)
        # Editing: keep the id so the service updates rather than inserts.
        return replace(self._original, **values)

    def _field_widgets(self) -> Mapping[str, QWidget]:
        return {
            "datetime": self._datetime_edit,
            "amount": self._amount_edit,
            "cash_account_id": self._cash_combo,
            "account_id": self._account_combo,
            "notes": self._notes_edit,
        }
