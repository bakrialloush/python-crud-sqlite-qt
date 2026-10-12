"""The SQLite schema.

Every statement is idempotent so :meth:`app.core.database.Database.connect` can
run the whole tuple on each startup without checking what already exists.
"""

from __future__ import annotations

CURRENCIES_TABLE = """
CREATE TABLE IF NOT EXISTS currencies (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    name   TEXT    NOT NULL,
    code   TEXT    NOT NULL,
    rate   TEXT    NOT NULL,
    method TEXT    NOT NULL CHECK (method IN ('mul', 'div'))
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

SCHEMA_STATEMENTS: tuple[str, ...] = (
    CURRENCIES_TABLE,
    CURRENCY_CODE_INDEX,
    ACCOUNTS_TABLE,
    ACCOUNTS_CURRENCY_INDEX,
)
