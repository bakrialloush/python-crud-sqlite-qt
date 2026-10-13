"""Display formatting for domain values.

Lives in the presentation layer so the domain stays free of display concerns,
while the table models, the dialogs and the tooltips all share one definition.
"""

from __future__ import annotations

from dataclasses import dataclass
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


@dataclass(frozen=True)
class TransactionTypeText:
    """The words one transaction type uses across the dialogs and pages.

    One record per type, so the dialog's field labels, the page's headings and
    the messages both show cannot drift apart. Adding a type is one entry here
    rather than edits scattered over the widgets — the same reason the split
    signs live on the enum instead of in the form.
    """

    #: Capitalised singular, for a page heading: "Payment".
    label: str
    #: Lower-case singular, for button text and sentence middles: "payment".
    noun: str
    #: Lower-case plural, for the search box and status line: "payments".
    plural: str
    #: The counterparty field's label: "Paid to" / "Received from".
    counterparty_label: str
    #: Placeholder for the notes field.
    notes_placeholder: str
    #: Connects the amount to the counterparty in a description: "to" / "from".
    preposition: str
    #: How the amount leaves or enters the cash account: "out of" / "into".
    flow: str
    #: Shown when the ledger has no asset account to post against yet.
    no_cash_message: str


#: One entry per member of :class:`TransactionType`, so a new type cannot be
#: added to the enum without someone deciding what it reads as.
_TRANSACTION_TEXT: dict[TransactionType, TransactionTypeText] = {
    TransactionType.PAYMENT: TransactionTypeText(
        label="Payment",
        noun="payment",
        plural="payments",
        counterparty_label="Paid to",
        notes_placeholder="What this payment was for",
        preposition="to",
        flow="out of",
        no_cash_message=(
            "Create an asset account first — a payment has to come out of one."
        ),
    ),
    TransactionType.RECEIPT: TransactionTypeText(
        label="Receipt",
        noun="receipt",
        plural="receipts",
        counterparty_label="Received from",
        notes_placeholder="What this receipt was for",
        preposition="from",
        flow="into",
        no_cash_message=(
            "Create an asset account first — a receipt has to come into one."
        ),
    ),
}

#: The timestamp format, spelled for Qt's date widgets. The table and the form
#: both render through it, and it has to keep agreeing with the storage format
#: in ``app.repositories.transaction_repository`` — a mismatch would show the
#: user a time the database does not hold. The layers cannot share a constant
#: without breaking the import rule, so the two are kept in step by hand.
DATETIME_QT_FORMAT = "yyyy-MM-dd HH:mm"

#: The date-only format, for the reports that filter by day rather than instant.
#: The leading half of the timestamp format above, so the two cannot read as
#: different dates for the same value.
DATE_QT_FORMAT = "yyyy-MM-dd"


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
    return transaction_text(transaction_type).label


def transaction_text(transaction_type: TransactionType) -> TransactionTypeText:
    """The display words for ``transaction_type``, all in one record.

    The dialog and the page read their labels from here rather than holding
    their own copy, so the same type reads the same way in both.
    """
    return _TRANSACTION_TEXT[transaction_type]


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


def format_debit(balance: Decimal) -> str:
    """Render a signed ledger figure for the debit side, or blank.

    The reports split one signed figure — debits positive, credits negative —
    into two columns, and which column it lands in follows from the sign rather
    than from anything the row carries. The other side is blank rather than "0",
    so a column reads as the side that has something in it and two figures can
    be compared down the page.

    Shared by the trial balance and the ledger, which draw the same two columns
    from the same convention.
    """
    return format_decimal(balance) if balance > 0 else ""


def format_credit(balance: Decimal) -> str:
    """Render a signed ledger figure for the credit side, shown positive, or blank."""
    return format_decimal(-balance) if balance < 0 else ""
