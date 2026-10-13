"""The SQLite schema.

Every statement is idempotent so :meth:`app.core.database.Database.connect` can
run the whole tuple on each startup without checking what already exists. The
one statement that cannot be idempotent on its own — adding a column to a table
that already exists — carries its own check, in :data:`COLUMN_ADDITIONS`.
"""

from __future__ import annotations

# ``is_base`` marks the currency every other rate is quoted against. Stored as
# SQLite's nearest thing to a boolean, since it has no BIT or BOOLEAN type.
CURRENCIES_TABLE = """
CREATE TABLE IF NOT EXISTS currencies (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    name    TEXT    NOT NULL,
    code    TEXT    NOT NULL,
    rate    TEXT    NOT NULL,
    method  TEXT    NOT NULL CHECK (method IN ('mul', 'div')),
    is_base INTEGER NOT NULL DEFAULT 0 CHECK (is_base IN (0, 1))
)
"""

# The rate is TEXT, not REAL: SQLite has no DECIMAL type, and a binary float
# would corrupt money values. The application stores ``str(Decimal)`` and reads
# it back with ``Decimal(text)``, so precision survives the round trip.
#
# Case-insensitive uniqueness, because "usd" and "USD" are the same currency.
# The application upper-cases codes before saving; the index keeps the rule true
# for any caller that does not.
CURRENCY_CODE_INDEX = """
CREATE UNIQUE INDEX IF NOT EXISTS idx_currencies_code ON currencies (UPPER(code))
"""

# At most one base, enforced rather than assumed. A partial index says so
# directly: unique over the base flag, but only across the rows that set it, so
# any number of rows may leave it at 0.
BASE_CURRENCY_INDEX = """
CREATE UNIQUE INDEX IF NOT EXISTS idx_currencies_base
    ON currencies (is_base) WHERE is_base = 1
"""

ACCOUNTS_TABLE = """
CREATE TABLE IF NOT EXISTS accounts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL,
    currency_id INTEGER NOT NULL REFERENCES currencies (id) ON DELETE RESTRICT,
    type        TEXT    NOT NULL
                        CHECK (type IN ('asset', 'liability', 'equity', 'revenue', 'expense'))
)
"""

ACCOUNTS_CURRENCY_INDEX = """
CREATE INDEX IF NOT EXISTS idx_accounts_currency ON accounts (currency_id)
"""

# ``datetime`` is TEXT holding an ISO 8601 timestamp. SQLite has no date type,
# and ``YYYY-MM-DD HH:MM:SS`` is both sortable and round-trippable through
# ``datetime.fromisoformat``. ``amount`` is TEXT for the same reason
# ``currencies.rate`` is: an exact ``Decimal``, not a binary float.
#
# Both account columns are ON DELETE RESTRICT, so an account that a transaction
# touched cannot be deleted out from under its ledger history. The service
# refuses this first, with a message naming how many transactions block it; the
# foreign key is the backstop for a caller that bypasses the service.
#
# The CHECK on ``type`` mirrors the accounts table's, and carries the same
# limitation: SQLite cannot alter a CHECK, so widening :class:`TransactionType`
# later means rebuilding this table rather than adding an entry to
# :data:`COLUMN_ADDITIONS`. It is kept because the repository writes the column
# from an enum, and the constraint is what holds that true for any other writer.
#
# ``account_id`` is the counterparty — the account paid for a payment, the
# account received from for a receipt — so it is named for the side it holds
# rather than for one direction. ``cash_account_id`` is always the asset side.
TRANSACTIONS_TABLE = """
CREATE TABLE IF NOT EXISTS transactions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    datetime        TEXT    NOT NULL,
    type            TEXT    NOT NULL CHECK (type IN ('payment', 'receipt')),
    cash_account_id INTEGER NOT NULL REFERENCES accounts (id) ON DELETE RESTRICT,
    account_id      INTEGER NOT NULL REFERENCES accounts (id) ON DELETE RESTRICT,
    amount          TEXT    NOT NULL,
    notes           TEXT    NOT NULL DEFAULT ''
)
"""

# One row per account per transaction: the double-entry posting. The amounts are
# signed — positive debits, negative credits — so the two rows of a transaction
# sum to zero and the sign, rather than the column order, says which is which.
#
# ON DELETE CASCADE, unlike the account columns above: a split has no life of
# its own and is meaningless without the transaction that posted it, so deleting
# the transaction is meant to take its splits with it. That is also why the
# generic repository needs no delete hook — the database does it.
SPLITS_TABLE = """
CREATE TABLE IF NOT EXISTS splits (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id INTEGER NOT NULL REFERENCES transactions (id) ON DELETE CASCADE,
    account_id     INTEGER NOT NULL REFERENCES accounts (id) ON DELETE RESTRICT,
    amount         TEXT    NOT NULL
)
"""

# The transactions table is ordered newest first, which is how a ledger is read.
TRANSACTIONS_DATETIME_INDEX = """
CREATE INDEX IF NOT EXISTS idx_transactions_datetime ON transactions (datetime)
"""

# Both split lookups are by a foreign key that every read and every account
# delete has to follow.
SPLITS_TRANSACTION_INDEX = """
CREATE INDEX IF NOT EXISTS idx_splits_transaction ON splits (transaction_id)
"""

SPLITS_ACCOUNT_INDEX = """
CREATE INDEX IF NOT EXISTS idx_splits_account ON splits (account_id)
"""

#: Tables, before anything that names a column in one.
TABLE_STATEMENTS: tuple[str, ...] = (
    CURRENCIES_TABLE,
    ACCOUNTS_TABLE,
    TRANSACTIONS_TABLE,
    SPLITS_TABLE,
)

#: Columns added to a table after it first shipped, as
#: ``(table, column, statement that adds it)``.
#:
#: ``CREATE TABLE IF NOT EXISTS`` leaves an existing table exactly as it was, so
#: a database created before a column existed would never gain it. Each entry
#: names the column it adds, and ``Database.connect`` runs the statement only
#: when that column is missing — which makes the whole tuple idempotent, like
#: the statements around it. ``ALTER TABLE`` cannot add a CHECK constraint, so
#: the column arrives unchecked; the application is what keeps it 0 or 1.
COLUMN_ADDITIONS: tuple[tuple[str, str, str], ...] = (
    (
        "currencies",
        "is_base",
        "ALTER TABLE currencies ADD COLUMN is_base INTEGER NOT NULL DEFAULT 0",
    ),
)

#: Indexes last: one of them names a column an older database only gains above.
INDEX_STATEMENTS: tuple[str, ...] = (
    CURRENCY_CODE_INDEX,
    BASE_CURRENCY_INDEX,
    ACCOUNTS_CURRENCY_INDEX,
    TRANSACTIONS_DATETIME_INDEX,
    SPLITS_TRANSACTION_INDEX,
    SPLITS_ACCOUNT_INDEX,
)
