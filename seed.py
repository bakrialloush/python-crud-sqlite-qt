"""The seed dataset, and the two ways it runs.

    python seed.py     # clear both tables, then write the seed rows

Startup runs it too: `main.py` populates a database that holds nothing yet, so
the app never opens on two empty tables. A missing file needs no separate check —
opening one creates it with an empty schema, which is the same "no rows"
condition, one step earlier.

The startup path only ever inserts. Deleting is left to the command line, where
the user asked for it, so a bug in the emptiness check costs a stray row rather
than the user's data.

Both paths go through the services rather than raw SQL, so the seed rows face
the same validation and foreign keys the UI does — a seed that could not be
typed into a form is a seed that hides a bug.
"""

from __future__ import annotations

from decimal import Decimal

from app.config import DEFAULT_DATABASE_PATH
from app.core.database import Database
from app.domain.account import Account
from app.domain.currency import Currency
from app.domain.enums import AccountType, RateMethod
from app.repositories.account_repository import SqliteAccountRepository
from app.repositories.currency_repository import SqliteCurrencyRepository
from app.services.account_service import AccountService
from app.services.currency_service import CurrencyService

# USD is treated as the base currency, so converting an amount into it is the
# identity: a rate of 1, multiplied. A currency that is not the base would carry
# the rate that converts the base into it.
USD = Currency(name="US Dollar", code="USD", rate=Decimal("1"), method=RateMethod.MUL)

# "الصندوق" — the till, the account cash is held in.
CASH_ACCOUNT_NAME = "الصندوق"


def clear(
    database: Database, currencies: CurrencyService, accounts: AccountService
) -> None:
    """Delete every row, accounts before currencies.

    The accounts go first because a currency still in use cannot be deleted —
    the service refuses, and the foreign key would refuse it a second time
    underneath. Only the command line calls this.
    """
    for account in accounts.list_all():
        accounts.delete(account.id)
    for currency in currencies.list_all():
        currencies.delete(currency.id)

    # ``AUTOINCREMENT`` never reuses a value on its own — that is its whole
    # point — so without this the ids would climb on every run even though the
    # rows are new. Restarting the counters keeps a re-run identical.
    with database.transaction() as cursor:
        cursor.execute(
            "DELETE FROM sqlite_sequence WHERE name IN ('currencies', 'accounts')"
        )


def populate(
    currencies: CurrencyService, accounts: AccountService
) -> tuple[Currency, Account]:
    """Insert the seed rows and return what was stored."""
    usd = currencies.create(USD)
    # Second, because the account stores the id the currency was given on insert.
    cash = accounts.create(
        Account(name=CASH_ACCOUNT_NAME, currency_id=usd.id, type=AccountType.ASSET)
    )
    return usd, cash


def seed_if_empty(
    currencies: CurrencyService, accounts: AccountService
) -> bool:
    """Populate the database if it holds nothing yet, reporting whether it did.

    "Nothing yet" means neither table has a row. Both are checked rather than
    one: a user who added a currency and no accounts has started work, and the
    seed would collide with their code.
    """
    if currencies.list_all() or accounts.list_all():
        return False

    populate(currencies, accounts)
    return True


def main() -> None:
    database = Database(DEFAULT_DATABASE_PATH)
    database.connect()
    try:
        currency_repository = SqliteCurrencyRepository(database)
        account_repository = SqliteAccountRepository(database)

        currencies = CurrencyService(currency_repository, account_repository)
        accounts = AccountService(account_repository, currency_repository)

        clear(database, currencies, accounts)
        usd, cash = populate(currencies, accounts)

        # ASCII only: the Windows console cannot encode the account name.
        print(f"currency {usd.code} (id {usd.id})")
        print(f"account  id {cash.id}, type {cash.type.value}, currency {usd.code}")
        print(f"Seeded {database.path}")
    finally:
        database.close()


if __name__ == "__main__":
    main()
