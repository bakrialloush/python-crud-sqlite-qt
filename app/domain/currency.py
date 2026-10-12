"""The Currency entity and its invariants."""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal

from app.domain.enums import RateMethod
from app.domain.validation import (
    require_currency_code,
    require_name,
    require_positive_rate,
)


@dataclass
class Currency:
    """A unit of money, with the rate used to convert amounts into it."""

    name: str
    code: str
    rate: Decimal
    method: RateMethod
    # Declared last so the required fields stay first; a defaulted field may not
    # precede a required one. This ordering also lets the repository rebuild a
    # saved entity with ``dataclasses.replace``.
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
