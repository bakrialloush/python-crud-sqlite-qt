"""The Account entity and its invariants."""

from __future__ import annotations

from dataclasses import dataclass, replace

from app.domain.enums import AccountType
from app.domain.errors import ValidationError
from app.domain.validation import require_name


@dataclass
class Account:
    """A named account denominated in a single currency."""

    name: str
    currency_id: int
    type: AccountType
    # Last, for the same reason as ``Currency.id``.
    id: int | None = None

    def normalized(self) -> Account:
        """Return a copy with cosmetic noise stripped from the text fields."""
        return replace(self, name=self.name.strip())

    def validate(self) -> None:
        """Raise :class:`ValidationError` if this account cannot be stored.

        Only rules intrinsic to the account live here. Whether ``currency_id``
        actually points at a currency is a question about another entity, so
        ``AccountService`` owns that one.
        """
        require_name(self.name)
        if not isinstance(self.currency_id, int) or self.currency_id <= 0:
            raise ValidationError("A currency must be selected.", field="currency_id")
        if not isinstance(self.type, AccountType):
            raise ValidationError("A valid account type must be selected.", field="type")
