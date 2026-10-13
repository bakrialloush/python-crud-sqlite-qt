"""One account's line in a transaction."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass
class Split:
    """A single account's line in a transaction.

    The amount is signed, following the accounting convention the rest of the
    model uses: positive is a debit, negative is a credit. A transaction's two
    splits are posted together and sum to zero — see
    :meth:`app.domain.transaction.Transaction.splits`, which is the only place
    that decides how they are derived.
    """

    account_id: int
    amount: Decimal
    # Set when the split is read back from the database. A freshly derived split
    # names no transaction, because the one holding it is the transaction.
    transaction_id: int | None = None
    # Last, for the same reason as ``Currency.id``.
    id: int | None = None

    @property
    def is_debit(self) -> bool:
        """Whether this split debits its account, i.e. carries a positive amount."""
        return self.amount > 0
