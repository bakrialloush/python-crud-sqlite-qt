"""Create and edit form for a currency."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import replace
from decimal import Decimal

from PyQt6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from app.domain.currency import Currency
from app.domain.enums import RateMethod
from app.domain.errors import ValidationError
from app.domain.validation import MAX_NAME_LENGTH, parse_decimal
from app.ui.dialogs.form_support import (
    DIALOG_MINIMUM_WIDTH,
    build_button_box,
    build_form_layout,
    report_validation_error,
)
from app.ui.formatting import format_decimal, rate_method_description, rate_method_label

#: Raised by the service to reject a currency; called before the dialog closes.
CurrencyValidator = Callable[[Currency], None]

#: Shown on the form for the base currency, whose rate and method are fixed.
BASE_CURRENCY_NOTE = (
    "The base currency is what every other rate is quoted against, so it always "
    "converts at a rate of 1, multiplied. Only its name and code can be changed."
)


class CurrencyDialog(QDialog):
    """One form for both creating and editing.

    ``currency`` selects the mode: ``None`` creates a new one, an existing entity
    edits it and keeps its id. Validation is injected rather than implemented
    here, so the rules stay in the service — but they run while the form is still
    open, so the user reads the message with the field in front of them.

    The base currency is the one row this form edits only in part: its rate and
    method are what being the base *means*, so they arrive locked.
    """

    def __init__(
        self,
        validator: CurrencyValidator,
        currency: Currency | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._validator = validator
        self._original = currency
        self._result: Currency | None = None

        self.setWindowTitle("Edit currency" if currency is not None else "New currency")
        self.setModal(True)
        self.setMinimumWidth(DIALOG_MINIMUM_WIDTH)

        form = self._build_fields()
        self._populate()
        self._lock_base_fields()

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        note = self._build_base_note()
        if note is not None:
            layout.addWidget(note)
        layout.addWidget(build_button_box(self))

    @property
    def currency(self) -> Currency | None:
        """The validated currency, or ``None`` if the dialog was not accepted."""
        return self._result

    def accept(self) -> None:
        """Close only when the currency is valid; otherwise keep the form open."""
        try:
            currency = self._build_currency()
            self._validator(currency)
        except ValidationError as error:
            report_validation_error(self, error, self._field_widgets())
            return
        self._result = currency
        super().accept()

    def _build_fields(self) -> QFormLayout:
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("US Dollar")
        self._name_edit.setMaxLength(MAX_NAME_LENGTH)

        self._code_edit = QLineEdit()
        self._code_edit.setPlaceholderText("USD")
        self._code_edit.setMaxLength(10)

        # A plain line edit rather than a spin box: a QDoubleSpinBox would route
        # the rate through a C double and reintroduce the rounding that Decimal
        # exists to avoid.
        self._rate_edit = QLineEdit()
        self._rate_edit.setPlaceholderText("1")

        self._method_group, self._method_buttons = self._build_method_buttons()

        form = build_form_layout()
        form.addRow("Name", self._name_edit)
        form.addRow("Code", self._code_edit)
        form.addRow("Rate", self._rate_edit)
        form.addRow("Method", self._method_group)
        return form

    def _build_method_buttons(self) -> tuple[QWidget, dict[RateMethod, QRadioButton]]:
        """A radio button per rate method, in a group that allows only one."""
        container = QWidget()
        row = QHBoxLayout(container)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(16)

        group = QButtonGroup(container)
        buttons: dict[RateMethod, QRadioButton] = {}
        for method in RateMethod:
            label = f"{rate_method_label(method)}  ({rate_method_description(method)})"
            button = QRadioButton(label)
            group.addButton(button)
            row.addWidget(button)
            buttons[method] = button
        row.addStretch()
        return container, buttons

    def _populate(self) -> None:
        if self._original is None:
            self._rate_edit.setText("1")
            self._select_method(RateMethod.MUL)
            return
        self._name_edit.setText(self._original.name)
        self._code_edit.setText(self._original.code)
        self._rate_edit.setText(format_decimal(self._original.rate))
        self._select_method(self._original.method)

    @property
    def _editing_base(self) -> bool:
        """Whether this form is editing the base currency."""
        return self._original is not None and self._original.is_base

    def _lock_base_fields(self) -> None:
        """Grey out the rate and method when editing the base currency.

        They are not values the base can hold: converting into it is the
        identity, so its rate is 1 and its method multiply, and
        ``Currency.validate`` refuses anything else. Disabling rather than
        hiding keeps the form's shape the same and shows what the base means.
        """
        if not self._editing_base:
            return
        for widget in (self._rate_edit, self._method_group):
            widget.setEnabled(False)
            widget.setToolTip(BASE_CURRENCY_NOTE)

    def _build_base_note(self) -> QLabel | None:
        """A line saying why the fields above are locked, or ``None`` if none are."""
        if not self._editing_base:
            return None
        note = QLabel(BASE_CURRENCY_NOTE)
        note.setObjectName("hint")
        note.setWordWrap(True)
        return note

    def _select_method(self, method: RateMethod) -> None:
        button = self._method_buttons.get(method)
        if button is not None:
            button.setChecked(True)

    def _selected_method(self) -> RateMethod | None:
        for method, button in self._method_buttons.items():
            if button.isChecked():
                return method
        return None

    def _build_currency(self) -> Currency:
        """Build a currency from the form.

        Raises:
            ValidationError: if the rate cannot be parsed.
        """
        rate: Decimal = parse_decimal(self._rate_edit.text(), field="rate")

        method = self._selected_method()
        if method is None:
            raise ValidationError("Method must be 'mul' or 'div'.", field="method")

        values = {
            "name": self._name_edit.text(),
            "code": self._code_edit.text(),
            "rate": rate,
            "method": method,
        }
        if self._original is None:
            return Currency(**values)
        # Editing: keep the id so the service updates rather than inserts.
        return replace(self._original, **values)

    def _field_widgets(self) -> Mapping[str, QWidget]:
        return {
            "name": self._name_edit,
            "code": self._code_edit,
            "rate": self._rate_edit,
            "method": self._method_group,
        }
