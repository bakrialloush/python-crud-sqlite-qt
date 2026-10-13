"""The seed dataset, and the two ways it runs.

    python seed.py     # clear every table, then write the seed rows

Startup runs it too: `main.py` populates a database that holds nothing yet, so
the app never opens on blank tables. A missing file needs no separate check —
opening one creates it with an empty schema, which is the same "no rows"
condition, one step earlier.

The startup path only ever inserts. Deleting is left to the command line, where
the user asked for it, so a bug in the emptiness check costs a stray row rather
than the user's data.

Both paths go through the services rather than raw SQL, so the seed rows face
the same validation and foreign keys the UI does — a seed that could not be
typed into a form is a seed that hides a bug. The one field the form does not
offer, ``is_base``, is the base currency flag: it says which currency the other
rates are quoted against, and there is exactly one, so it belongs to the dataset
rather than to a row the user can edit.
"""

from __future__ import annotations

from app.config import DEFAULT_DATABASE_PATH
from app.core.database import Database
from app.domain.account import Account
from app.domain.currency import BASE_RATE, Currency
from app.domain.enums import AccountType, RateMethod
from app.repositories.account_repository import SqliteAccountRepository
from app.repositories.currency_repository import SqliteCurrencyRepository
from app.repositories.transaction_repository import SqliteTransactionRepository
from app.services.account_service import AccountService
from app.services.currency_service import CurrencyService
from app.services.transaction_service import TransactionService

# USD is the base currency: every other rate is a conversion from it, which is
# why its own conversion is the identity — a rate of 1, multiplied. The other
# three fields follow from being the base, and ``Currency.validate`` holds them
# there, so this row is the one an unedited form cannot produce.
USD = Currency(
    name="US Dollar",
    code="USD",
    rate=BASE_RATE,
    method=RateMethod.MUL,
    is_base=True,
)

# "الصندوق" — the till, the account cash is held in.
CASH_ACCOUNT_NAME = "الصندوق"

# "المصروفات" — expenses. The seed needs a second account because a payment
# moves money between two of them: with the till alone there would be nothing to
# pay, and the Payments tab would be inert on a fresh database.
EXPENSES_ACCOUNT_NAME = "المصروفات"


def clear(
    database: Database,
    currencies: CurrencyService,
    accounts: AccountService,
    transactions: TransactionService,
) -> None:
    """Delete every row, transactions before accounts before currencies.

    The order is the reverse of the foreign keys, and the foreign keys are what
    insist on it: both of a transaction's account columns, and the account on
    every split, are ON DELETE RESTRICT — so an account a payment touched cannot
    go until the payment does, and a currency cannot go while an account is held
    in it. Only the command line calls this.
    """
    for transaction in transactions.list_all():
        transactions.delete(transaction.id)
    for account in accounts.list_all():
        accounts.delete(account.id)
    for currency in currencies.list_all():
        # ``allow_base`` because this run deletes the base only to write it
        # again a moment later; the service refuses that for every other caller.
        currencies.delete(currency.id, allow_base=True)

    # ``AUTOINCREMENT`` never reuses a value on its own — that is its whole
    # point — so without this the ids would climb on every run even though the
    # rows are new. Restarting the counters keeps a re-run identical.
    with database.transaction() as cursor:
        cursor.execute(
            "DELETE FROM sqlite_sequence WHERE name IN "
            "('currencies', 'accounts', 'transactions', 'splits')"
        )


def populate(
    currencies: CurrencyService, accounts: AccountService
) -> tuple[Currency, Account, Account]:
    """Insert the seed rows and return what was stored."""
    usd = currencies.create(USD)
    # Both accounts come second, because they store the id the currency was
    # given on insert.
    cash = accounts.create(
        Account(name=CASH_ACCOUNT_NAME, currency_id=usd.id, type=AccountType.ASSET)
    )
    expenses = accounts.create(
        Account(
            name=EXPENSES_ACCOUNT_NAME,
            currency_id=usd.id,
            type=AccountType.EXPENSE,
        )
    )
    return usd, cash, expenses


def seed_if_empty(
    currencies: CurrencyService,
    accounts: AccountService,
    transactions: TransactionService,
) -> bool:
    """Populate the database if it holds nothing yet, reporting whether it did.

    "Nothing yet" means no table has a row. All of them are checked rather than
    one: a user who added a currency and no accounts has started work, and the
    seed would collide with their code.
    """
    if currencies.list_all() or accounts.list_all() or transactions.list_all():
        return False

    populate(currencies, accounts)
    return True


def main() -> None:
    database = Database(DEFAULT_DATABASE_PATH)
    database.connect()
    try:
        currency_repository = SqliteCurrencyRepository(database)
        account_repository = SqliteAccountRepository(database)
        transaction_repository = SqliteTransactionRepository(database)

        currencies = CurrencyService(currency_repository, account_repository)
        accounts = AccountService(
            account_repository, currency_repository, transaction_repository
        )
        transactions = TransactionService(transaction_repository, account_repository)

        clear(database, currencies, accounts, transactions)
        usd, cash, expenses = populate(currencies, accounts)

        # ASCII only: the Windows console cannot encode the account names.
        print(f"currency {usd.code} (id {usd.id}, base)")
        print(f"account  id {cash.id}, type {cash.type.value}, currency {usd.code}")
        print(f"account  id {expenses.id}, type {expenses.type.value}, currency {usd.code}")
        print(f"Seeded {database.path}")
    finally:
        database.close()


if __name__ == "__main__":
    main()
