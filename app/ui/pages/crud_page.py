"""Shared behaviour for the CRUD tabs.

A subclass supplies three things — how to open the create/edit form, how to
delete a row, and how to describe a row for the delete prompt. Everything else
(search, selection state, the status line, error reporting, refreshing) is
written once here, so a new entity gets a working tab by implementing three
short methods.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Generic, Protocol, TypeVar

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QLabel, QMessageBox, QVBoxLayout, QWidget

from app.domain.errors import AppError
from app.ui.models.base_table_model import BaseTableModel
from app.ui.widgets.crud_toolbar import CrudToolbar
from app.ui.widgets.table_view import build_filter_proxy, build_table_view

T = TypeVar("T")


class ListService(Protocol[T]):
    """What a page needs from a service in order to display rows. Nothing more.

    Declared here, where it is consumed, and only as wide as the consumer needs
    — the pages call the rest of the service API directly.
    """

    def list_all(self) -> Sequence[T]:
        """Every row to display."""


class CrudPage(QWidget, Generic[T]):
    """A searchable table with add, edit, delete and refresh actions.

    ``T`` is the row type: ``Currency`` for the currencies tab, ``AccountView``
    for the accounts one, since that table shows a joined projection.
    """

    #: Emitted after a successful write, so other tabs can refresh themselves.
    data_changed = pyqtSignal()

    def __init__(
        self,
        *,
        service: ListService[T],
        model: BaseTableModel[T],
        title: str,
        entity_label: str,
        plural_label: str,
        name_column: int = 1,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._service = service
        self._model = model
        self._entity_label = entity_label
        self._plural_label = plural_label
        self._build(title=title, name_column=name_column)
        self._connect()
        self.reload()

    # ------------------------------------------------------------- public API
    def reload(self) -> None:
        """Re-read the rows from the service.

        Public because another tab may change the data this one displays.
        """
        try:
            rows = self._service.list_all()
        except AppError as error:
            self._report(error)
            return
        self._model.set_items(rows)
        self._toolbar.set_actions_enabled(False)
        self._refresh_status()

    def selected_item(self) -> T | None:
        """The selected row, or ``None`` when nothing is selected."""
        indexes = self._table.selectionModel().selectedRows()
        if not indexes:
            return None
        # Rows arrive in proxy coordinates; the model knows nothing about them.
        source_index = self._proxy.mapToSource(indexes[0])
        return self._model.item_at(source_index.row())

    # ---------------------------------------------------------------- assembly
    def _build(self, *, title: str, name_column: int) -> None:
        self._proxy = build_filter_proxy()
        self._proxy.setSourceModel(self._model)

        self._table = build_table_view(stretch_column=name_column)
        self._table.setModel(self._proxy)

        self._toolbar = CrudToolbar(
            entity_label=self._entity_label,
            plural_label=self._plural_label,
            parent=self,
        )

        heading = QLabel(title)
        heading.setObjectName("title")

        self._status = QLabel()
        self._status.setObjectName("hint")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        layout.addWidget(heading)
        layout.addWidget(self._toolbar)
        layout.addWidget(self._table, 1)
        layout.addWidget(self._status)

    def _connect(self) -> None:
        self._toolbar.add_requested.connect(self._on_add)
        self._toolbar.edit_requested.connect(self._on_edit)
        self._toolbar.delete_requested.connect(self._on_delete)
        self._toolbar.refresh_requested.connect(self.reload)
        self._toolbar.search_changed.connect(self._on_search)
        self._table.doubleClicked.connect(self._on_edit)
        self._table.selectionModel().selectionChanged.connect(self._on_selection_changed)

    # ---------------------------------------------------------------- handlers
    def _on_add(self, *_: object) -> None:
        if self._prompt(None):
            self._after_change()

    def _on_edit(self, *_: object) -> None:
        current = self.selected_item()
        if current is not None and self._prompt(current):
            self._after_change()

    def _on_delete(self, *_: object) -> None:
        current = self.selected_item()
        if current is None:
            return

        confirmed = QMessageBox.question(
            self,
            f"Delete {self._entity_label}",
            f"Delete {self._describe(current)}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirmed != QMessageBox.StandardButton.Yes:
            return

        if self._attempt(lambda: self._remove(current)):
            self._after_change()

    def _on_search(self, text: str) -> None:
        self._proxy.setFilterFixedString(text)
        self._refresh_status()

    def _on_selection_changed(self, *_: object) -> None:
        self._toolbar.set_actions_enabled(self.selected_item() is not None)

    # ------------------------------------------------------------------ helpers
    def _after_change(self) -> None:
        self.reload()
        self.data_changed.emit()

    def _attempt(self, action: Callable[[], object]) -> bool:
        """Run a write, reporting any expected failure. True if it succeeded."""
        try:
            action()
        except AppError as error:
            self._report(error)
            return False
        return True

    def _report(self, error: AppError) -> None:
        """Show an expected failure. Deliberately narrow: a bug should not land here."""
        QMessageBox.warning(self, "Something went wrong", str(error))

    def _refresh_status(self) -> None:
        total = self._model.rowCount()
        visible = self._proxy.rowCount()
        if visible == total:
            noun = self._entity_label if total == 1 else self._plural_label
            self._status.setText(f"{total} {noun}")
        else:
            self._status.setText(f"{visible} of {total} {self._plural_label}")

    # -------------------------------------------------------------------- hooks
    def _prompt(self, item: T | None) -> bool:
        """Show the create (``item is None``) or edit form, then persist it.

        Returns ``True`` only when something was saved. Reporting a rejected save
        is this method's job, so the caller has nothing to decide but whether to
        reload.
        """
        raise NotImplementedError

    def _remove(self, item: T) -> None:
        """Delete ``item``, raising :class:`~app.domain.errors.AppError` on failure."""
        raise NotImplementedError

    def _describe(self, item: T) -> str:
        """One-line description of ``item``, for the delete confirmation."""
        raise NotImplementedError
