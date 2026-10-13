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

#: Tables, before anything that names a column in one.
TABLE_STATEMENTS: tuple[str, ...] = (
    CURRENCIES_TABLE,
    ACCOUNTS_TABLE,
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
)
