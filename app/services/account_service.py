"""Account use cases."""

from __future__ import annotations

from app.domain.account import Account
from app.domain.currency import Currency
from app.domain.errors import (
    ConstraintViolation,
    NotFoundError,
    ReferentialIntegrityError,
    ValidationError,
)
from app.domain.views import AccountView
from app.repositories.interfaces import (
    AccountRepository,
    CurrencyRepository,
    TransactionRepository,
)


class AccountService:
    """Create, read, update and delete accounts.

    An account's own rules live on the entity. The rules here are the ones that
    need another entity: that the selected currency actually exists, and that no
    transaction has posted to the account before it is removed.
    """

    def __init__(
        self,
        accounts: AccountRepository,
        currencies: CurrencyRepository,
        transactions: TransactionRepository,
    ) -> None:
        self._accounts = accounts
        self._currencies = currencies
        self._transactions = transactions

    def list_all(self) -> list[AccountView]:
        """Every account, with its currency's code and name for display."""
        return self._accounts.list_all_views()

    def list_currencies(self) -> list[Currency]:
        """The currencies an account can be denominated in.

        Read fresh on every dialog open, so the picker cannot go stale when a
        currency is added or renamed on the other tab.
        """
        return self._currencies.list_all()

    def get(self, account_id: int) -> Account:
        """The account with ``account_id``.

        Raises:
            NotFoundError: if there is no such account.
        """
        account = self._accounts.get(account_id)
        if account is None:
            raise NotFoundError(f"No account with id {account_id}.")
        return account

    def validate(self, account: Account) -> None:
        """Raise :class:`ValidationError` if ``account`` cannot be saved."""
        account.validate()
        if self._currencies.get(account.currency_id) is None:
            raise ValidationError(
                "The selected currency no longer exists.", field="currency_id"
            )

    def create(self, account: Account) -> Account:
        """Validate and store a new account, returning it with its id."""
        candidate = account.normalized()
        self.validate(candidate)
        return self._accounts.add(candidate)

    def update(self, account: Account) -> Account:
        """Validate and overwrite an existing account."""
        if account.id is None:
            raise ValidationError("Cannot update an account that has not been saved yet.")
        candidate = account.normalized()
        self.validate(candidate)
        return self._accounts.update(candidate)

    def delete(self, account_id: int) -> None:
        """Delete an account that no transaction has posted to.

        Raises:
            NotFoundError: if there was no such account.
            ReferentialIntegrityError: if a transaction still posts to it.
        """
        account = self.get(account_id)

        refusal = self._refusal_for(account)
        if refusal is not None:
            raise ReferentialIntegrityError(refusal)

        try:
            self._accounts.delete(account_id)
        except ConstraintViolation as error:
            # The count above and the delete are not atomic, and a caller could
            # bypass this service entirely. The foreign key is the backstop that
            # keeps the rule true either way.
            raise ReferentialIntegrityError(
                f"{account.name} is still referenced and cannot be deleted."
            ) from error

    def delete_refusal(self, account_id: int) -> str | None:
        """Why the account cannot be deleted, or ``None`` when it can.

        The page shows this on the disabled Delete button. It is presentation
        only: ``_refusal_for`` decides nothing the service does not already
        decide, and :meth:`delete` refuses for the same reason.
        """
        account = self._accounts.get(account_id)
        if account is None:
            return None
        return self._refusal_for(account)

    def _refusal_for(self, account: Account) -> str | None:
        """The reason one account cannot go, from its transactions alone.

        One sentence, worded once, so the tooltip the user reads before acting
        and the error they would get after are the same rule said the same way.
        A payment and a receipt both count: either would lose ledger history.
        """
        if account.id is None:
            # Never stored, so nothing can refer to it. Asked to refuse anyway.
            return None

        blockers = self._transactions.count_by_account(account.id)
        if not blockers:
            return None
        noun = "transaction" if blockers == 1 else "transactions"
        them = "it" if blockers == 1 else "them"
        return (
            f"{account.name} is used by {blockers} {noun} and cannot be deleted. "
            f"Delete {them} first."
        )