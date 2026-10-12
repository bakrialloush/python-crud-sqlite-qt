"""Create and edit form for an account."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import replace

from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from app.domain.account import Account
from app.domain.currency import Currency
from app.domain.enums import AccountType
from app.domain.errors import ValidationError
from app.domain.validation import MAX_NAME_LENGTH
from app.ui.dialogs.form_support import (
    DIALOG_MINIMUM_WIDTH,
    build_button_box,
    build_form_layout,
    report_validation_error,
)
from app.ui.formatting import account_type_label

#: Raised by the service to reject an account; called before the dialog closes.
AccountValidator = Callable[[Account], None]


class AccountDialog(QDialog):
    """One form for both creating and editing.

    ``account`` selects the mode, exactly as ``currency`` does for
    :class:`~app.ui.dialogs.currency_dialog.CurrencyDialog`. The caller is
    responsible for supplying at least one currency — the page checks before
    opening this, so the picker is never empty.
    """

    def __init__(
        self,
        currencies: Sequence[Currency],
        validator: AccountValidator,
        account: Account | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._currencies = tuple(currencies)
        self._validator = validator
        self._original = account
        self._result: Account | None = None

        self.setWindowTitle("Edit account" if account is not None else "New account")
        self.setModal(True)
        self.setMinimumWidth(DIALOG_MINIMUM_WIDTH)

        form = self._build_fields()
        self._populate()

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(build_button_box(self))

    @property
    def account(self) -> Account | None:
        """The validated account, or ``None`` if the dialog was not accepted."""
        return self._result

    def accept(self) -> None:
        """Close only when the account is valid; otherwise keep the form open."""
        try:
            account = self._build_account()
            self._validator(account)
        except ValidationError as error:
            report_validation_error(self, error, self._field_widgets())
            return
        self._result = account
        super().accept()

    def _build_fields(self) -> QFormLayout:
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("Everyday account")
        self._name_edit.setMaxLength(MAX_NAME_LENGTH)

        self._type_combo = QComboBox()
        for account_type in AccountType:
            self._type_combo.addItem(account_type_label(account_type), account_type)

        # Each entry carries its Currency as user data, so the selection reads
        # back as a domain object instead of an index into a parallel list.
        self._currency_combo = QComboBox()
        for currency in self._currencies:
            self._currency_combo.addItem(f"{currency.code} — {currency.name}", currency)

        form = build_form_layout()
        form.addRow("Name", self._name_edit)
        form.addRow("Type", self._type_combo)
        form.addRow("Currency", self._currency_combo)
        return form

    def _populate(self) -> None:
        if self._original is None:
            self._select_data(self._type_combo, AccountType.ASSET)
            return
        self._name_edit.setText(self._original.name)
        self._select_data(self._type_combo, self._original.type)
        self._select_data(self._currency_combo, self._original.currency_id, key="id")

    @staticmethod
    def _select_data(combo: QComboBox, value: object, *, key: str | None = None) -> None:
        """Select the entry carrying ``value``, comparing ``key`` when given."""
        for index in range(combo.count()):
            data = combo.itemData(index)
            candidate = getattr(data, key) if key is not None else data
            if candidate == value:
                combo.setCurrentIndex(index)
                return

    def _build_account(self) -> Account:
        """Build an account from the form.

        Raises:
            ValidationError: if no currency is selected.
        """
        currency = self._currency_combo.currentData()
        if not isinstance(currency, Currency):
            raise ValidationError("A currency must be selected.", field="currency_id")

        account_type = self._type_combo.currentData()
        if not isinstance(account_type, AccountType):
            raise ValidationError("A valid account type must be selected.", field="type")

        values = {
            "name": self._name_edit.text(),
            "currency_id": currency.id,
            "type": account_type,
        }
        if self._original is None:
            return Account(**values)
        return replace(self._original, **values)

    def _field_widgets(self) -> Mapping[str, QWidget]:
        return {
            "name": self._name_edit,
            "type": self._type_combo,
            "currency_id": self._currency_combo,
        }
