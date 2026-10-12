"""Shared table-model plumbing.

A subclass declares its headers and how one column of one item renders. The Qt
boilerplate — row and column counts, role dispatch, reset notifications — is
written once, here.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Generic, TypeVar

from PyQt6.QtCore import QAbstractTableModel, QModelIndex, Qt

T = TypeVar("T")


class BaseTableModel(QAbstractTableModel, Generic[T]):
    """A read-only table over a sequence of domain objects."""

    #: Column captions, in display order. A subclass's renderers must match this
    #: length and order — see :meth:`display`.
    headers: tuple[str, ...] = ()

    def __init__(self, items: Sequence[T] = ()) -> None:
        super().__init__()
        self._items: list[T] = list(items)

    # ----------------------------------------------------------- Qt overrides
    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._items)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.headers)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> object:
        if not index.isValid():
            return None

        item = self._items[index.row()]
        # PyQt6 compares Qt's role enums against the plain ints Qt passes in,
        # so these are direct comparisons rather than conversions.
        if role == Qt.ItemDataRole.DisplayRole:
            return self.display(item, index.column())
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return self.alignment(index.column())
        if role == Qt.ItemDataRole.ToolTipRole:
            return self.tooltip(item, index.column())
        if role == Qt.ItemDataRole.UserRole:
            return item
        return None

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> object:
        if orientation != Qt.Orientation.Horizontal:
            return None
        if role != Qt.ItemDataRole.DisplayRole or not 0 <= section < len(self.headers):
            return None
        return self.headers[section]

    # ------------------------------------------------------------------ own API
    def set_items(self, items: Sequence[T]) -> None:
        """Replace the contents, notifying attached views exactly once."""
        self.beginResetModel()
        self._items = list(items)
        self.endResetModel()

    def item_at(self, row: int) -> T:
        """The item behind ``row``. Callers must pass a source-model row."""
        return self._items[row]

    # -------------------------------------------------------------------- hooks
    def display(self, item: T, column: int) -> str:
        """Text for ``item`` in ``column``. Required."""
        raise NotImplementedError

    def alignment(self, column: int) -> Qt.AlignmentFlag:
        """Alignment for ``column``. Left-aligned unless overridden."""
        return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter

    def tooltip(self, item: T, column: int) -> str | None:
        """Tooltip for ``item`` in ``column``, or ``None`` for no tooltip."""
        return None
