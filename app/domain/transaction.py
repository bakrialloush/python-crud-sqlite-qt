"""The Transaction entity and its invariants."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime as DateTime
from decimal import Decimal

from app.domain.enums import TransactionType
from app.domain.errors import ValidationError
from app.domain.split import Split
from app.domain.validation import require_notes, require_positive_decimal


@dataclass
class Transaction:
    """Money moved between two accounts, posted as two splits.

    The ``datetime`` type is imported as ``DateTime`` so the field does not
    shadow the type it is annotated with. The field keeps the plain name because
    that is what the column and the user call it.
    """

    datetime: DateTime
    type: TransactionType
    cash_account_id: int
    payment_account_id: int
    amount: Decimal
    notes: str = ""
    # Last, for the same reason as ``Currency.id``.
    id: int | None = None

    def splits(self) -> tuple[Split, Split]:
        """The two postings this transaction makes.

        The single definition of how a transaction of this type posts: the
        account being paid is debited and the cash account credited, so the two
        always sum to zero. The repository writes exactly these, and a later
        balance figure would read them — neither re-derives the rule.

        ``amount`` is positive by validation, so applying the type's signs is
        what turns it into a debit and a credit.
        """
        return (
            Split(
                account_id=self.payment_account_id,
                amount=self.amount * self.type.counterparty_sign,
            ),
            Split(
                account_id=self.cash_account_id,
                amount=self.amount * self.type.cash_sign,
            ),
        )

    def normalized(self) -> Transaction:
        """Return a copy with cosmetic noise stripped from the text fields."""
        return replace(self, notes=self.notes.strip())

    def validate(self) -> None:
        """Raise :class:`ValidationError` if this transaction cannot be stored.

        Only rules intrinsic to the transaction live here. Whether the two
        accounts exist, whether the cash one is an asset, and whether they share
        a currency are all questions about other entities, so
        ``TransactionService`` owns those.
        """
        if not isinstance(self.datetime, DateTime):
            raise ValidationError("A date and time must be given.", field="datetime")
        if not isinstance(self.type, TransactionType):
            raise ValidationError(
                "A valid transaction type must be selected.", field="type"
            )
        self._require_account_selected("cash_account_id", self.cash_account_id)
        self._require_account_selected("payment_account_id", self.payment_account_id)
        if self.cash_account_id == self.payment_account_id:
            # A posting that debits and credits the same account moves nothing,
            # and the two splits would cancel out unseen.
            raise ValidationError(
                "The cash account and the account being paid must be different.",
                field="payment_account_id",
            )
        require_positive_decimal(self.amount, field="amount", label="Amount")
        require_notes(self.notes)

    @staticmethod
    def _require_account_selected(field: str, account_id: int) -> None:
        if not isinstance(account_id, int) or account_id <= 0:
            raise ValidationError("An account must be selected.", field=field)
