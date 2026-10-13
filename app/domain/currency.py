"""The Currency entity and its invariants."""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal

from app.domain.enums import RateMethod
from app.domain.errors import ValidationError
from app.domain.validation import (
    require_currency_code,
    require_name,
    require_positive_rate,
)

#: The rate of the base currency. Every other rate is expressed as a conversion
#: *from* the base, so converting an amount into the base changes nothing.
BASE_RATE = Decimal("1")


@dataclass
class Currency:
    """A unit of money, with the rate used to convert amounts into it."""

    name: str
    code: str
    rate: Decimal
    method: RateMethod
    # The defaulted fields are declared last; a defaulted field may not precede
    # a required one. This ordering also lets the repository rebuild a saved
    # entity with ``dataclasses.replace``.
    #
    # ``is_base`` is set by the seed alone. It is not a choice the form offers,
    # because it is not a property of the currency so much as of the set: it
    # names the one currency the others are quoted against.
    is_base: bool = False
    id: int | None = None

    def convert(self, amount: Decimal) -> Decimal:
        """Convert ``amount`` from the base currency into this one."""
        return self.method.apply(amount, self.rate)

    def normalized(self) -> Currency:
        """Return a copy with cosmetic noise stripped from the text fields.

        Applied before saving so a code entered as ``" usd "`` is stored as
        ``"USD"`` — matching the case-insensitive unique index on the table.
        """
        return replace(self, name=self.name.strip(), code=self.code.strip().upper())

    def validate(self) -> None:
        """Raise :class:`ValidationError` if this currency cannot be stored."""
        require_name(self.name)
        require_currency_code(self.code)
        require_positive_rate(self.rate)
        if not isinstance(self.method, RateMethod):
            raise ValidationError("Method must be 'mul' or 'div'.", field="method")
        if self.is_base:
            # Not a preference: a rate of 1 multiplied is what "the currency the
            # others are quoted against" means. The form locks both fields, and
            # this is what holds for a caller that does not go through it.
            if self.rate != BASE_RATE:
                raise ValidationError(
                    "The base currency always converts at a rate of 1.", field="rate"
                )
            if self.method is not RateMethod.MUL:
                raise ValidationError(
                    "The base currency always converts by multiplying.", field="method"
                )
