"""Display formatting for domain values.

Lives in the presentation layer so the domain stays free of display concerns,
while the table models, the dialogs and the tooltips all share one definition.
"""

from __future__ import annotations

from decimal import Decimal

from app.domain.enums import AccountType, RateMethod

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


def account_type_label(account_type: AccountType) -> str:
    """Human-readable account type, e.g. ``"Liability"``."""
    return _ACCOUNT_TYPE_LABELS[account_type]


def rate_method_label(method: RateMethod) -> str:
    """Human-readable rate method, e.g. ``"multiply"``."""
    return _RATE_METHOD_LABELS[method]


def rate_method_description(method: RateMethod) -> str:
    """How the method combines an amount and a rate, for the dialog and tooltips."""
    return f"amount {method.symbol} rate"


def format_decimal(value: Decimal) -> str:
    """Render a Decimal for display, without trailing zeros or exponent form.

    ``Decimal("3.7500")`` becomes ``"3.75"`` rather than ``"3.7500"``, and
    ``Decimal("100")`` stays ``"100"`` rather than normalising to ``"1E+2"``.
    """
    normalized = value.normalize()
    if normalized == normalized.to_integral_value():
        return str(normalized.quantize(Decimal(1)))
    return format(normalized, "f")
