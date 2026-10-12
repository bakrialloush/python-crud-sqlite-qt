"""The application's light theme.

All three steps in :func:`apply_light_theme` are necessary on Windows 11. The
native style follows the operating system's light/dark setting and ignores much
of Qt's stylesheet language, so an app that asks for a light theme would still
come up dark for someone running Windows in dark mode. The Fusion style makes
the palette and the stylesheet authoritative, and setting the palette explicitly
pins the light colours regardless of what the system is set to.
"""

from __future__ import annotations

from string import Template

from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QApplication

_WINDOW = QColor("#f6f7f9")
_TEXT = QColor("#1f2328")
_MUTED = QColor("#5c636d")
_DISABLED = QColor("#9aa1ab")
_BASE = QColor("#ffffff")
_ALTERNATE = QColor("#f2f4f7")
_HIGHLIGHT = QColor("#2f6feb")
_HIGHLIGHT_HOVER = QColor("#2258c9")
_HIGHLIGHTED = QColor("#ffffff")
_BORDER = QColor("#d6dae0")

# Kept as a Template rather than an f-string: QSS is full of braces, and doubling
# every one of them would make this unreadable.
_STYLESHEET = Template(
    """
QMainWindow, QDialog {
    background-color: $window;
}

QTabWidget::pane {
    border: 1px solid $border;
    background-color: $base;
}

QTabBar::tab {
    padding: 8px 18px;
    margin-right: 3px;
    border: 1px solid $border;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    background-color: $alternate;
    color: $muted;
}

QTabBar::tab:selected {
    background-color: $base;
    color: $text;
    font-weight: 600;
}

QTabBar::tab:hover:!selected {
    background-color: $window;
}

QLabel#title {
    font-size: 17px;
    font-weight: 600;
    color: $text;
}

QLabel#hint {
    color: $muted;
}

QTableView {
    background-color: $base;
    alternate-background-color: $alternate;
    border: 1px solid $border;
    border-radius: 6px;
    gridline-color: $border;
    selection-background-color: $highlight;
    selection-color: $highlighted;
}

QHeaderView::section {
    background-color: $alternate;
    color: $muted;
    padding: 7px 10px;
    border: none;
    border-right: 1px solid $border;
    border-bottom: 1px solid $border;
    font-weight: 600;
}

QLineEdit, QComboBox {
    background-color: $base;
    border: 1px solid $border;
    border-radius: 6px;
    padding: 6px 9px;
    selection-background-color: $highlight;
    selection-color: $highlighted;
}

QLineEdit:focus, QComboBox:focus {
    border-color: $highlight;
}

QComboBox::drop-down {
    border: none;
    width: 22px;
}

QPushButton {
    background-color: $base;
    border: 1px solid $border;
    border-radius: 6px;
    padding: 6px 14px;
}

QPushButton:hover {
    background-color: $alternate;
}

QPushButton:pressed {
    background-color: $border;
}

QPushButton:disabled {
    background-color: $window;
    border-color: $border;
}

QPushButton#primary {
    background-color: $highlight;
    border-color: $highlight;
    color: $highlighted;
    font-weight: 600;
}

QPushButton#primary:hover {
    background-color: $highlightHover;
}

QPushButton#primary:disabled {
    background-color: $border;
    border-color: $border;
}

QStatusBar {
    background-color: $window;
    color: $muted;
}

QToolTip {
    background-color: $base;
    color: $text;
    border: 1px solid $border;
}
"""
)


def apply_light_theme(app: QApplication) -> None:
    """Force a light appearance, whatever the operating system is set to."""
    app.setStyle("Fusion")
    app.setPalette(_light_palette())
    app.setStyleSheet(_STYLESHEET.substitute(_palette_values()))


def _palette_values() -> dict[str, str]:
    return {
        "window": _WINDOW.name(),
        "text": _TEXT.name(),
        "muted": _MUTED.name(),
        "base": _BASE.name(),
        "alternate": _ALTERNATE.name(),
        "highlight": _HIGHLIGHT.name(),
        "highlightHover": _HIGHLIGHT_HOVER.name(),
        "highlighted": _HIGHLIGHTED.name(),
        "border": _BORDER.name(),
    }


def _light_palette() -> QPalette:
    """An explicit light palette.

    Only the roles Fusion actually consults are set; filling in every role would
    be noise. The Disabled group matters because Fusion greys out controls from
    the palette, and a stale dark value there would look broken.
    """
    palette = QPalette()
    role = QPalette.ColorRole
    group = QPalette.ColorGroup

    palette.setColor(role.Window, _WINDOW)
    palette.setColor(role.WindowText, _TEXT)
    palette.setColor(role.Base, _BASE)
    palette.setColor(role.AlternateBase, _ALTERNATE)
    palette.setColor(role.ToolTipBase, _BASE)
    palette.setColor(role.ToolTipText, _TEXT)
    palette.setColor(role.Text, _TEXT)
    palette.setColor(role.Button, _BASE)
    palette.setColor(role.ButtonText, _TEXT)
    palette.setColor(role.BrightText, _HIGHLIGHTED)
    palette.setColor(role.Highlight, _HIGHLIGHT)
    palette.setColor(role.HighlightedText, _HIGHLIGHTED)
    palette.setColor(role.PlaceholderText, _DISABLED)

    for disabled_role in (role.Text, role.WindowText, role.ButtonText):
        palette.setColor(group.Disabled, disabled_role, _DISABLED)

    return palette
