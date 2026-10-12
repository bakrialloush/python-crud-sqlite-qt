"""Generic SQLite CRUD, shared by every repository.

A concrete repository declares its table name and column list, then maps rows to
entities and back. The statements themselves are written once, here — so adding
an entity means adding a subclass and changing nothing below.

Concrete entities must be dataclasses with an ``id`` attribute, which is what
lets :func:`dataclasses.replace` stamp the generated primary key onto a saved
entity without a per-entity hook.
"""

from __future__ import annotations

import sqlite3
from abc import ABC, abstractmethod
from dataclasses import replace
from typing import ClassVar, Generic, TypeVar, cast

from app.core.database import Database
from app.domain.errors import NotFoundError

T = TypeVar("T")


class SqliteRepository(Generic[T], ABC):
    """CRUD over a single table, driven by two subclass hooks.

    Subclass contract:

    * ``table``   — the table name.
    * ``columns`` — the writable columns, in the order :meth:`_to_parameters`
      returns them. The primary key is not included; it is handled here.
    """

    table: ClassVar[str]
    columns: ClassVar[tuple[str, ...]]

    def __init__(self, database: Database) -> None:
        self._database = database

    # ----------------------------------------------------------- subclass hooks
    @abstractmethod
    def _to_entity(self, row: sqlite3.Row) -> T:
        """Build an entity from a result row."""

    @abstractmethod
    def _to_parameters(self, entity: T) -> tuple[object, ...]:
        """Values for ``columns``, excluding the primary key."""

    # -------------------------------------------------------------------- reads
    def get(self, entity_id: int) -> T | None:
        """The entity with ``entity_id``, or ``None``."""
        rows = self._database.query(
            f"SELECT {self._selection} FROM {self.table} WHERE id = ?", (entity_id,)
        )
        return self._to_entity(rows[0]) if rows else None

    def list_all(self) -> list[T]:
        """Every row, ordered by primary key."""
        rows = self._database.query(
            f"SELECT {self._selection} FROM {self.table} ORDER BY id"
        )
        return [self._to_entity(row) for row in rows]

    # ------------------------------------------------------------------- writes
    def add(self, entity: T) -> T:
        """Insert ``entity`` and return it carrying its new id.

        Returning the saved entity rather than mutating the argument keeps this
        honest for frozen dataclasses and stops callers from holding a stale
        ``id`` of ``None``.
        """
        column_list = ", ".join(self.columns)
        placeholders = ", ".join("?" for _ in self.columns)
        with self._database.transaction() as cursor:
            cursor.execute(
                f"INSERT INTO {self.table} ({column_list}) VALUES ({placeholders})",
                self._to_parameters(entity),
            )
            new_id = cursor.lastrowid
        return replace(entity, id=new_id)

    def update(self, entity: T) -> T:
        """Overwrite the stored row matching ``entity.id``."""
        entity_id = self._entity_id(entity)
        if entity_id is None:
            raise NotFoundError(f"Cannot update an unsaved {type(entity).__name__}.")

        assignments = ", ".join(f"{column} = ?" for column in self.columns)
        with self._database.transaction() as cursor:
            cursor.execute(
                f"UPDATE {self.table} SET {assignments} WHERE id = ?",
                (*self._to_parameters(entity), entity_id),
            )
            if cursor.rowcount == 0:
                raise NotFoundError(f"No {type(entity).__name__} with id {entity_id}.")
        return entity

    def delete(self, entity_id: int) -> bool:
        """Delete the row, reporting whether anything was removed."""
        with self._database.transaction() as cursor:
            cursor.execute(f"DELETE FROM {self.table} WHERE id = ?", (entity_id,))
            return cursor.rowcount > 0

    # ------------------------------------------------------------------ helpers
    @property
    def _selection(self) -> str:
        """The select list: the primary key first, then the declared columns."""
        return ", ".join(("id", *self.columns))

    def _entity_id(self, entity: T) -> int | None:
        """Primary key of ``entity``.

        Override if an entity ever keys itself differently; the default assumes
        the ``id`` attribute every entity in this project declares.
        """
        return cast("int | None", getattr(entity, "id", None))
