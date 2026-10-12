"""Read models: projections assembled for display, never stored as tables."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.enums import AccountType


@dataclass(frozen=True)
class AccountView:
    """An account joined with the display fields of its currency.

    The accounts table needs the currency's code and name, so this carries them
    instead of making the presentation layer resolve the reference per row.
    """

    id: int
    name: str
    type: AccountType
    currency_id: int
    currency_code: str
    currency_name: str
