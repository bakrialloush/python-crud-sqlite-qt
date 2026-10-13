"""Display formatting for domain values.

Lives in the presentation layer so the domain stays free of display concerns,
while the table models, the dialogs and the tooltips all share one definition.
"""

from __future__ import annotations

from datetime import datetime as DateTime
from decimal import Decimal

from app.domain.enums import AccountType, RateMethod, TransactionType

_ACCOUNT_TYPE_LABELS: dict[AccountType, str] = {
    AccountType.ASSET: "Asset",
    AccountType.LIABILITY: "Liability",
    AccountType.EQUITY: "Equity",
    AccountType.REVENUE: "Revenue",
    AccountType.EXPENSE: "Expense",
}

_RATE_METHOD_LABELS: dict[RateMethod, str] = {
    RateMethod.MUL: "multiply",
    RateMethod.DIV: "divide",
}

_TRANSACTION_TYPE_LABELS: dict[TransactionType, str] = {
    TransactionType.PAYMENT: "Payment",
}

#: The timestamp format, spelled for Qt's date widgets. The table and the form
#: both render through it, and it has to keep agreeing with the storage format
#: in ``app.repositories.transaction_repository`` — a mismatch would show the
#: user a time the database does not hold. The layers cannot share a constant
#: without breaking the import rule, so the two are kept in step by hand.
DATETIME_QT_FORMAT = "yyyy-MM-dd HH:mm"


def account_type_label(account_type: AccountType) -> str:
    """Human-readable account type, e.g. ``"Liability"``."""
    return _ACCOUNT_TYPE_LABELS[account_type]


def rate_method_label(method: RateMethod) -> str:
    """Human-readable rate method, e.g. ``"multiply"``."""
    return _RATE_METHOD_LABELS[method]


def rate_method_description(method: RateMethod) -> str:
    """How the method combines an amount and a rate, for the dialog and tooltips."""
    return f"amount {method.symbol} rate"


def transaction_type_label(transaction_type: TransactionType) -> str:
    """Human-readable transaction type, e.g. ``"Payment"``."""
    return _TRANSACTION_TYPE_LABELS[transaction_type]


def format_datetime(value: DateTime) -> str:
    """Render a timestamp for display, in the shape the database stores.

    Deliberately the same text as the stored value: what the user reads in the
    table is what an edit would put back unchanged.
    """
    return value.strftime("%Y-%m-%d %H:%M")


def format_decimal(value: Decimal) -> str:
    """Render a Decimal for display, without trailing zeros or exponent form.

    ``Decimal("3.7500")`` becomes ``"3.75"`` rather than ``"3.7500"``, and
    ``Decimal("100")`` stays ``"100"`` rather than normalising to ``"1E+2"``.
    """
    normalized = value.normalize()
    if normalized == normalized.to_integral_value():
        return str(normalized.quantize(Decimal(1)))
    return format(normalized, "f")
