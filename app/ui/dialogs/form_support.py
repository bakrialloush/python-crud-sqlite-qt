"""Pieces shared by the create/edit dialogs.

Plain functions rather than a common base class. Each dialog stays an ordinary
``QDialog`` whose ``__init__`` builds its own widgets, so there is no
base-class hook ordering to reason about, while the behaviour both dialogs need
is still written once.
"""

from __future__ import annotations

from collections.abc import Mapping

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QMessageBox,
    QWidget,
)

from app.domain.errors import ValidationError

DIALOG_MINIMUM_WIDTH = 380


def build_form_layout() -> QFormLayout:
    """The standard two-column form, with fields taking the free width."""
    form = QFormLayout()
    form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
    form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    form.setVerticalSpacing(10)
    return form


def build_button_box(dialog: QDialog) -> QDialogButtonBox:
    """A Save/Cancel box wired to the dialog's ``accept`` and ``reject``."""
    box = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
    )
    save_button = box.button(QDialogButtonBox.StandardButton.Save)
    save_button.setObjectName("primary")
    save_button.setDefault(True)
    save_button.setText("Save")
    box.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancel")
    box.accepted.connect(dialog.accept)
    box.rejected.connect(dialog.reject)
    return box


def report_validation_error(
    dialog: QDialog,
    error: ValidationError,
    field_widgets: Mapping[str, QWidget],
) -> None:
    """Show the message and move the cursor to the field that caused it.

    The caller keeps the dialog open, so the user can fix one value without the
    form closing and losing what they had already entered.
    """
    QMessageBox.warning(dialog, "Cannot save", str(error))
    widget = field_widgets.get(error.field or "")
    if widget is not None:
        widget.setFocus()
