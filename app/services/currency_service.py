"""Currency use cases."""

from __future__ import annotations

from app.domain.currency import Currency
from app.domain.errors import (
    ConstraintViolation,
    NotFoundError,
    ReferentialIntegrityError,
    ValidationError,
)
from app.repositories.interfaces import AccountRepository, CurrencyRepository


class CurrencyService:
    """Create, read, update and delete currencies.

    Rules intrinsic to a currency (a name, a valid code, a positive rate) live on
    the entity. The rules here are the ones that need the rest of the set to
    decide: whether a code is already taken, whether any account still refers to
    a currency, and whether it is the base the others are quoted against.
    """

    def __init__(
        self,
        currencies: CurrencyRepository,
        accounts: AccountRepository,
    ) -> None:
        self._currencies = currencies
        self._accounts = accounts

    def list_all(self) -> list[Currency]:
        """Every currency."""
        return self._currencies.list_all()

    def get(self, currency_id: int) -> Currency:
        """The currency with ``currency_id``.

        Raises:
            NotFoundError: if there is no such currency.
        """
        currency = self._currencies.get(currency_id)
        if currency is None:
            raise NotFoundError(f"No currency with id {currency_id}.")
        return currency

    def validate(self, currency: Currency) -> None:
        """Raise :class:`ValidationError` if ``currency`` cannot be saved.

        Public because the edit dialog calls it before closing: the service stays
        the single source of truth for the rules, while the user still gets the
        message with the form in front of them.
        """
        currency.validate()
        if self._currencies.exists_by_code(currency.code, exclude_id=currency.id):
            raise ValidationError(
                f"Another currency already uses the code {currency.code.strip().upper()}.",
                field="code",
            )

    def create(self, currency: Currency) -> Currency:
        """Validate and store a new currency, returning it with its id."""
        candidate = currency.normalized()
        self.validate(candidate)
        return self._currencies.add(candidate)

    def update(self, currency: Currency) -> Currency:
        """Validate and overwrite an existing currency."""
        if currency.id is None:
            raise ValidationError("Cannot update a currency that has not been saved yet.")
        candidate = currency.normalized()
        self.validate(candidate)
        return self._currencies.update(candidate)

    def delete(self, currency_id: int, *, allow_base: bool = False) -> None:
        """Delete a currency that no account uses.

        Args:
            currency_id: the currency to delete.
            allow_base: whether the base currency may go. Only the seeding
                command passes this, because it deletes the base in order to
                rebuild it; nothing in the application should.

        Raises:
            ValidationError: if it is the base currency.
            ReferentialIntegrityError: if any account still refers to it.
        """
        currency = self.get(currency_id)

        if currency.is_base and not allow_base:
            # Every other rate is a conversion from the base, so deleting it
            # would leave the rest quoting a currency that is not there.
            raise ValidationError(
                f"{currency.code} is the base currency and cannot be deleted."
            )

        blockers = self._accounts.count_by_currency(currency_id)
        if blockers:
            noun = "account" if blockers == 1 else "accounts"
            raise ReferentialIntegrityError(
                f"{currency.code} is used by {blockers} {noun} and cannot be deleted. "
                f"Delete or reassign {'it' if blockers == 1 else 'them'} first."
            )

        try:
            self._currencies.delete(currency_id)
        except ConstraintViolation as error:
            # The count above and the delete are not atomic, and a caller could
            # bypass this service entirely. The foreign key is the backstop that
            # keeps the rule true either way.
            raise ReferentialIntegrityError(
                f"{currency.code} is still referenced and cannot be deleted."
            ) from error
