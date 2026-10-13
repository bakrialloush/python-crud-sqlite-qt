"""The toolbar and search box shared by the CRUD pages."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLineEdit, QPushButton, QWidget


class CrudToolbar(QWidget):
    """Add, Edit, Delete and Refresh buttons plus a search box.

    Emits intent only. What each action means is the page's business, which is
    what keeps this widget usable for any entity.
    """

    add_requested = pyqtSignal()
    edit_requested = pyqtSignal()
    delete_requested = pyqtSignal()
    refresh_requested = pyqtSignal()
    search_changed = pyqtSignal(str)

    def __init__(
        self,
        *,
        entity_label: str,
        plural_label: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._build(entity_label, plural_label)
        self._connect()

    def set_actions_enabled(self, has_selection: bool) -> None:
        """Edit and Delete need a selected row; Add and Refresh never do."""
        self._edit_button.setEnabled(has_selection)
        self._delete_button.setEnabled(has_selection)
        # A refusal belongs to one selected row; a new selection starts clean.
        self._delete_button.setToolTip("")

    def set_delete_enabled(self, enabled: bool, reason: str = "") -> None:
        """Allow or refuse Delete for the selected row, explaining a refusal.

        ``set_actions_enabled`` covers "nothing is selected". This is for a row
        that is selected and still cannot go, so the reason sits on the button
        instead of in a message box the user has to provoke.
        """
        self._delete_button.setEnabled(enabled)
        self._delete_button.setToolTip(reason)

    def clear_search(self) -> None:
        """Reset the search box, which also clears the filter."""
        self._search_edit.clear()

    def _build(self, entity_label: str, plural_label: str) -> None:
        self._add_button = QPushButton(f"Add {entity_label}")
        self._add_button.setObjectName("primary")
        self._edit_button = QPushButton("Edit")
        self._delete_button = QPushButton("Delete")
        self._refresh_button = QPushButton("Refresh")

        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText(f"Search {plural_label}…")
        self._search_edit.setClearButtonEnabled(True)
        self._search_edit.setMinimumWidth(220)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(self._add_button)
        layout.addWidget(self._edit_button)
        layout.addWidget(self._delete_button)
        layout.addStretch(1)
        layout.addWidget(self._search_edit)
        layout.addWidget(self._refresh_button)

        self.set_actions_enabled(False)

    def _connect(self) -> None:
        self._add_button.clicked.connect(lambda: self.add_requested.emit())
        self._edit_button.clicked.connect(lambda: self.edit_requested.emit())
        self._delete_button.clicked.connect(lambda: self.delete_requested.emit())
        self._refresh_button.clicked.connect(lambda: self.refresh_requested.emit())
        self._search_edit.textChanged.connect(self.search_changed.emit)
