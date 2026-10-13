"""Field-level rules shared by the domain entities.

Centralising these keeps each rule — and its user-facing message — defined once,
so ``Currency`` and ``Account`` cannot drift apart on what a valid name is.

Each function raises :class:`ValidationError` and returns nothing; callers that
want the canonical value call ``entity.normalized()``.
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from app.domain.errors import ValidationError

MAX_NAME_LENGTH = 60

#: Notes are free text and optional, so only their length is a rule.
MAX_NOTES_LENGTH = 500

# One to ten non-space characters, upper-cased for comparison: "USD", "BTC",
# but also symbols like "$" or "€" and mixed forms like "US$".
CODE_PATTERN = re.compile(r"^\S{1,10}$")


def parse_decimal(text: str, *, field: str) -> Decimal:
    """Parse user-entered text into an exact :class:`~decimal.Decimal`.

    Deliberately not ``float``: routing a rate through a binary float would
    introduce rounding before the value ever reaches the database.
    """
    cleaned = text.strip().replace(",", "")
    if not cleaned:
        raise ValidationError("A value is required.", field=field)
    try:
        value = Decimal(cleaned)
    except InvalidOperation:
        raise ValidationError("Must be a number, for example 3.75.", field=field) from None
    if not value.is_finite():
        raise ValidationError("Must be a finite number.", field=field)
    return value


def require_name(value: str) -> None:
    """Require a non-blank name within :data:`MAX_NAME_LENGTH`."""
    name = value.strip()
    if not name:
        raise ValidationError("Name is required.", field="name")
    if len(name) > MAX_NAME_LENGTH:
        raise ValidationError(
            f"Name must be {MAX_NAME_LENGTH} characters or fewer.", field="name"
        )


def require_currency_code(value: str) -> None:
    """Require a 1-10 character code with no spaces, up-cased for comparison."""
    if not CODE_PATTERN.match(value.strip().upper()):
        raise ValidationError(
            "Code must be 1-10 characters with no spaces, for example USD or $.",
            field="code",
        )


def require_positive_decimal(value: Decimal, *, field: str, label: str) -> None:
    """Require a finite :class:`~decimal.Decimal` greater than zero.

    ``label`` names the field as the user sees it, so the message reads "Amount
    must be greater than zero". Each caller keeps its own name for the value
    while the rule itself — and the wording of the rule — stays in one place.
    """
    if not isinstance(value, Decimal) or not value.is_finite():
        raise ValidationError(f"{label} must be a number.", field=field)
    if value <= 0:
        raise ValidationError(f"{label} must be greater than zero.", field=field)


def require_positive_rate(value: Decimal) -> None:
    """Require a finite rate greater than zero.

    Zero is rejected because ``RateMethod.DIV`` would divide by it — this rule is
    what makes ``Currency.convert`` safe on the divide path.
    """
    require_positive_decimal(value, field="rate", label="Rate")


def require_notes(value: str) -> None:
    """Require notes within :data:`MAX_NOTES_LENGTH`, once trimmed.

    Blank is allowed: notes are optional, and only their length is a rule.
    """
    if len(value.strip()) > MAX_NOTES_LENGTH:
        raise ValidationError(
            f"Notes must be {MAX_NOTES_LENGTH} characters or fewer.", field="notes"
        )
