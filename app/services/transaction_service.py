"""Transaction use cases."""

from __future__ import annotations

from app.domain.account import Account
from app.domain.enums import AccountType
from app.domain.errors import NotFoundError, ValidationError
from app.domain.split import Split
from app.domain.transaction import Transaction
from app.domain.views import AccountView, TransactionView
from app.repositories.interfaces import AccountRepository, TransactionRepository


class TransactionService:
    """Create, read, update and delete transactions.

    Rules intrinsic to a transaction — a positive amount, two distinct accounts,
    a valid type — live on the entity. The rules here are the ones that need the
    accounts themselves: that both exist, that the cash side is an asset, and
    that the two are held in the same currency. A payment moves money rather
    than converting it, so a posting across two currencies is refused instead of
    being priced with a rate.
    """

    def __init__(
        self,
        transactions: TransactionRepository,
        accounts: AccountRepository,
    ) -> None:
        self._transactions = transactions
        self._accounts = accounts

    def list_all(self) -> list[TransactionView]:
        """Every transaction, with both account names, for display."""
        return self._transactions.list_all_views()

    def list_accounts(self) -> list[AccountView]:
        """The accounts a payment can be posted to.

        Read fresh on every dialog open, so the pickers cannot go stale when an
        account is added, renamed or removed on the other tab.
        """
        return self._accounts.list_all_views()

    def get(self, transaction_id: int) -> Transaction:
        """The transaction with ``transaction_id``.

        Raises:
            NotFoundError: if there is no such transaction.
        """
        transaction = self._transactions.get(transaction_id)
        if transaction is None:
            raise NotFoundError(f"No transaction with id {transaction_id}.")
        return transaction

    def splits_for(self, transaction_id: int) -> list[Split]:
        """The splits stored for ``transaction_id``.

        Empty for a transaction that does not exist or posted nothing, which is
        the truthful answer to the question — use :meth:`get` to insist that the
        transaction is there.
        """
        return self._transactions.list_splits(transaction_id)

    def validate(self, transaction: Transaction) -> None:
        """Raise :class:`ValidationError` if ``transaction`` cannot be saved.

        Public because the dialog calls it before closing: the service stays the
        single source of truth for the rules, while the user still gets the
        message with the form in front of them.
        """
        transaction.validate()
        cash = self._require_account(transaction.cash_account_id, "cash_account_id")
        if cash.type is not AccountType.ASSET:
            # The picker only offers assets; this is what holds the same rule
            # for a caller that does not go through it.
            raise ValidationError(
                "The cash account must be an asset account.", field="cash_account_id"
            )
        paid = self._require_account(
            transaction.payment_account_id, "payment_account_id"
        )
        if paid.currency_id != cash.currency_id:
            raise ValidationError(
                "A payment moves money between accounts held in the same currency.",
                field="payment_account_id",
            )

    def create(self, transaction: Transaction) -> Transaction:
        """Validate and store a new transaction, with its splits, returning it."""
        candidate = transaction.normalized()
        self.validate(candidate)
        return self._transactions.add(candidate)

    def update(self, transaction: Transaction) -> Transaction:
        """Validate and overwrite an existing transaction, rewriting its splits."""
        if transaction.id is None:
            raise ValidationError(
                "Cannot update a transaction that has not been saved yet."
            )
        candidate = transaction.normalized()
        self.validate(candidate)
        return self._transactions.update(candidate)

    def delete(self, transaction_id: int) -> None:
        """Delete a transaction. Its splits go with it.

        Raises:
            NotFoundError: if there was no such transaction.
        """
        if not self._transactions.delete(transaction_id):
            raise NotFoundError(f"No transaction with id {transaction_id}.")

    def _require_account(self, account_id: int, field: str) -> Account:
        """The account ``account_id``, or a validation error naming the field."""
        account = self._accounts.get(account_id)
        if account is None:
            raise ValidationError(
                "The selected account no longer exists.", field=field
            )
        return account
