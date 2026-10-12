"""Account use cases."""

from __future__ import annotations

from app.domain.account import Account
from app.domain.currency import Currency
from app.domain.errors import NotFoundError, ValidationError
from app.domain.views import AccountView
from app.repositories.interfaces import AccountRepository, CurrencyRepository


class AccountService:
    """Create, read, update and delete accounts.

    An account's own rules live on the entity. The rule here is the one that
    needs another entity: that the selected currency actually exists.
    """

    def __init__(
        self,
        accounts: AccountRepository,
        currencies: CurrencyRepository,
    ) -> None:
        self._accounts = accounts
        self._currencies = currencies

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
        """Delete an account.

        Raises:
            NotFoundError: if there was no such account.
        """
        if not self._accounts.delete(account_id):
            raise NotFoundError(f"No account with id {account_id}.")
