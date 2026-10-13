"""SQLite connection management.

The only module in the project that opens a database connection, so the pragmas
below cannot be bypassed by another caller.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path

from app.core.schema import COLUMN_ADDITIONS, INDEX_STATEMENTS, TABLE_STATEMENTS
from app.domain.errors import ConstraintViolation, PersistenceError


def _column_names(connection: sqlite3.Connection, table: str) -> set[str]:
    """The columns of ``table``, or an empty set if it does not exist yet."""
    rows = connection.execute(f"PRAGMA table_info({table})").fetchall()
    return {row["name"] for row in rows}


class Database:
    """Owns a single SQLite connection and the transaction boundary around it.

    One connection is enough: the UI is single-threaded and SQLite serialises
    writers anyway. Callers receive cursors and rows, never the raw connection,
    so the connection's configuration stays private.
    """

    def __init__(self, path: Path | str) -> None:
        self._path = Path(path)
        self._connection: sqlite3.Connection | None = None

    @property
    def path(self) -> Path:
        """Where the database file lives, for display."""
        return self._path

    def connect(self) -> None:
        """Open the connection, apply pragmas and ensure the schema exists.

        Idempotent, so it is safe to call from a context manager.
        """
        if self._connection is not None:
            return

        connection: sqlite3.Connection | None = None
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            # isolation_level=None turns off sqlite3's implicit transaction
            # handling, leaving `transaction()` as the single explicit place a
            # transaction is opened — which is what makes rollback reliable.
            connection = sqlite3.connect(self._path, isolation_level=None)
            # Per-connection and OFF by default: without this the ON DELETE
            # RESTRICT on accounts.currency_id is silently ignored.
            connection.execute("PRAGMA foreign_keys = ON")
            connection.row_factory = sqlite3.Row
            for statement in TABLE_STATEMENTS:
                connection.execute(statement)
            # Between the tables and the indexes: an index may name a column
            # that only these statements add.
            for table, column, statement in COLUMN_ADDITIONS:
                if column not in _column_names(connection, table):
                    connection.execute(statement)
            for statement in INDEX_STATEMENTS:
                connection.execute(statement)
        except (sqlite3.Error, OSError) as error:
            # Do not leak a half-configured connection when the schema fails.
            if connection is not None:
                connection.close()
            raise PersistenceError(f"Could not open the database: {error}") from error

        self._connection = connection

    def close(self) -> None:
        """Close the connection. Idempotent."""
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def query(self, sql: str, parameters: Sequence[object] = ()) -> list[sqlite3.Row]:
        """Run a read-only statement and return every row."""
        try:
            return list(self._require_connection().execute(sql, parameters).fetchall())
        except sqlite3.Error as error:
            raise PersistenceError(f"Could not read from the database: {error}") from error

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Cursor]:
        """Run writes as one unit, rolling back if anything goes wrong."""
        connection = self._require_connection()
        cursor = connection.cursor()
        cursor.execute("BEGIN")
        try:
            yield cursor
        except sqlite3.IntegrityError as error:
            connection.rollback()
            raise ConstraintViolation(str(error)) from error
        except sqlite3.Error as error:
            connection.rollback()
            raise PersistenceError(f"Could not write to the database: {error}") from error
        except Exception:
            connection.rollback()
            raise
        else:
            connection.commit()
        finally:
            cursor.close()

    def _require_connection(self) -> sqlite3.Connection:
        if self._connection is None:
            raise PersistenceError("The database connection is not open.")
        return self._connection
