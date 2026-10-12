"""Consistent configuration for the CRUD tables.

Every table in the application is configured the same way, so the settings live
here rather than being repeated per page — and cannot drift apart.
"""

from __future__ import annotations

from PyQt6.QtCore import QSortFilterProxyModel, Qt
from PyQt6.QtWidgets import QAbstractItemView, QHeaderView, QTableView


def build_table_view(*, stretch_column: int | None = None) -> QTableView:
    """A read-only, single-selection table view.

    Args:
        stretch_column: The column that absorbs leftover width. Without it the
            last column stretches instead.
    """
    view = QTableView()
    view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    # Editing happens in a dialog, never in the grid, so a stray double-click
    # cannot put a cell into edit mode.
    view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    view.setAlternatingRowColors(True)
    view.setShowGrid(False)
    view.verticalHeader().setVisible(False)

    header = view.horizontalHeader()
    header.setHighlightSections(False)
    header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    if stretch_column is None:
        header.setStretchLastSection(True)
    else:
        header.setSectionResizeMode(stretch_column, QHeaderView.ResizeMode.Stretch)

    return view


def build_filter_proxy() -> QSortFilterProxyModel:
    """A proxy that filters case-insensitively across every column.

    ``setFilterKeyColumn(-1)`` makes the proxy match against the display text of
    all columns at once, which is exactly what a search box wants. That is why
    there is no ``filterAcceptsRow`` override here.
    """
    proxy = QSortFilterProxyModel()
    proxy.setFilterKeyColumn(-1)
    proxy.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
    return proxy
