"""The Trial Balance tab.

A read-only report, so it shares nothing with :class:`~app.ui.pages.crud_page.CrudPage`
beyond the table helpers: there is no toolbar, no dialog, and no
``data_changed`` to emit. The tabs that do write reload it instead.
"""

from __future__ import annotations

from datetime import date

from PyQt6.QtCore import QDate, QModelIndex, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QDateEdit,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.domain.errors import AppError
from app.domain.views import TrialBalance, TrialBalanceRow
from app.services.trial_balance_service import TrialBalanceService
from app.ui.formatting import DATE_QT_FORMAT, format_decimal
from app.ui.models.trial_balance_table_model import TrialBalanceTableModel
from app.ui.widgets.table_view import build_filter_proxy, build_table_view

#: The account name is what wants the leftover width; the figures after it are
#: short and sized to their contents.
_STRETCH_COLUMN = 0


class TrialBalancePage(QWidget):
    """Every account's position over a chosen period, in its currency and in base.

    The period filters which transactions count, not which accounts appear: an
    account that posted nothing in the window is a zero row, and dropping those
    is the "Hide zero balances" toggle's job rather than the query's.
    """

    #: Emitted when a row is opened: which account to read the ledger of, and the
    #: period this report is showing, so the ledger opens on the same window
    #: rather than on one the reader has to set up again.
    account_activated = pyqtSignal(int, QDate, QDate)

    def __init__(
        self, service: TrialBalanceService, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._service = service
        #: The last report read, kept so the toggle can re-render without
        #: asking the service the same question again.
        self._balance: TrialBalance | None = None

        self._build()
        self._prefill_period()
        self._connect()
        self.reload()

    # ------------------------------------------------------------- public API
    def reload(self) -> None:
        """Re-read the report for the current period.

        Public because the tabs that write into the ledger change what this one
        displays, and the main window calls this when any of them reports a
        change.
        """
        try:
            self._balance = self._service.build(self._start_date(), self._end_date())
        except AppError as error:
            # Deliberately narrow, as on the CRUD pages: a bug should surface
            # loudly rather than as a message box.
            QMessageBox.warning(self, "Something went wrong", str(error))
            return

        self._model.set_items(self._visible_rows())
        self._refresh_footer()
        self._refresh_status()

    # ---------------------------------------------------------------- assembly
    def _build(self) -> None:
        self._model = TrialBalanceTableModel()

        self._proxy = build_filter_proxy()
        self._proxy.setSourceModel(self._model)

        self._table = build_table_view(stretch_column=_STRETCH_COLUMN)
        self._table.setModel(self._proxy)
        # The one thing a read-only report can be asked to do, so it is worth
        # saying out loud rather than leaving to be discovered.
        self._table.setToolTip("Double-click an account to read its ledger.")

        heading = QLabel("Trial Balance")
        heading.setObjectName("title")

        self._status = QLabel()
        self._status.setObjectName("hint")

        self._total = QLabel()

        footer = QHBoxLayout()
        footer.addWidget(self._status)
        footer.addStretch(1)
        footer.addWidget(self._total)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        layout.addWidget(heading)
        layout.addWidget(self._build_controls())
        layout.addWidget(self._table, 1)
        layout.addLayout(footer)

    def _build_controls(self) -> QWidget:
        """The period fields, the toggle, and the search box.

        The search is not a period filter: it narrows what is displayed through
        the proxy, while the dates decide what the service reads.
        """
        self._from_edit = self._date_edit()
        self._to_edit = self._date_edit()
        self._hide_zeros = QCheckBox("Hide zero balances")

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search accounts…")
        self._search.setClearButtonEnabled(True)
        self._search.setMinimumWidth(220)

        self._refresh = QPushButton("Refresh")

        bar = QWidget()
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(QLabel("From"))
        layout.addWidget(self._from_edit)
        layout.addWidget(QLabel("To"))
        layout.addWidget(self._to_edit)
        layout.addWidget(self._hide_zeros)
        layout.addStretch(1)
        layout.addWidget(self._search)
        layout.addWidget(self._refresh)
        return bar

    @staticmethod
    def _date_edit() -> QDateEdit:
        field = QDateEdit()
        field.setCalendarPopup(True)
        field.setDisplayFormat(DATE_QT_FORMAT)
        return field

    def _connect(self) -> None:
        self._from_edit.dateChanged.connect(self._on_from_changed)
        self._to_edit.dateChanged.connect(self._on_to_changed)
        self._hide_zeros.toggled.connect(self._on_hide_zeros_toggled)
        self._search.textChanged.connect(self._on_search)
        self._refresh.clicked.connect(lambda: self.reload())
        self._table.doubleClicked.connect(self._on_row_activated)

    def _prefill_period(self) -> None:
        """Open on the days the stored transactions cover.

        Nothing stored yet leaves both fields on today, which reports the same
        thing an empty range would while still reading as a date someone chose.
        """
        period = self._service.period()
        if period is None:
            today = QDate.currentDate()
            self._from_edit.setDate(today)
            self._to_edit.setDate(today)
        else:
            self._from_edit.setDate(self._qdate(period[0]))
            self._to_edit.setDate(self._qdate(period[1]))
        self._bound_dates()

    # ---------------------------------------------------------------- handlers
    def _on_from_changed(self, value: QDate) -> None:
        # Raising the start past the end is not something to refuse afterwards:
        # the end simply moves with it, so the pair is never upside down.
        self._constrain(self._to_edit, minimum=value)
        self.reload()

    def _on_to_changed(self, value: QDate) -> None:
        self._constrain(self._from_edit, maximum=value)
        self.reload()

    def _on_hide_zeros_toggled(self, *_: object) -> None:
        # Re-render only: dropping rows is a display choice, so the report the
        # service built already holds everything this needs.
        self._model.set_items(self._visible_rows())
        self._refresh_status()

    def _on_search(self, text: str) -> None:
        self._proxy.setFilterFixedString(text)
        self._refresh_status()

    def _on_row_activated(self, index: QModelIndex) -> None:
        """Ask for the row's account to be read as a ledger.

        The index arrives in proxy coordinates, so it is mapped before the model
        is asked for the row behind it — the same step the CRUD pages take for a
        selection. Where the ledger is and how it is shown is not this page's
        business; it reports what was opened and leaves the rest to the window.
        """
        row = self._model.item_at(self._proxy.mapToSource(index).row())
        self.account_activated.emit(
            row.account_id, self._from_edit.date(), self._to_edit.date()
        )

    # ------------------------------------------------------------------ helpers
    def _bound_dates(self) -> None:
        """Apply the initial bounds, so the two fields cannot cross."""
        self._constrain(self._from_edit, maximum=self._to_edit.date())
        self._constrain(self._to_edit, minimum=self._from_edit.date())

    @staticmethod
    def _constrain(
        field: QDateEdit,
        *,
        minimum: QDate | None = None,
        maximum: QDate | None = None,
    ) -> None:
        """Move a field's bound without echoing an event back to the reporter.

        A bound that clamps the field's current value would otherwise emit
        ``dateChanged`` and read the report a second time for one edit.
        """
        blocked = field.blockSignals(True)
        if minimum is not None:
            field.setMinimumDate(minimum)
        if maximum is not None:
            field.setMaximumDate(maximum)
        field.blockSignals(blocked)

    def _visible_rows(self) -> list[TrialBalanceRow]:
        """The accounts to show: all of them, less the zero ones if asked."""
        if self._balance is None:
            return []
        if not self._hide_zeros.isChecked():
            return list(self._balance.rows)
        return [row for row in self._balance.rows if row.balance]

    def _refresh_footer(self) -> None:
        """Show what the In Base column adds up to, and why it may not be zero."""
        if self._balance is None:
            self._total.setText("")
            self._total.setToolTip("")
            return

        total = self._balance.total_in_base
        self._total.setText(
            f"Total In Base ({self._balance.base_code}): {format_decimal(total)}"
        )
        self._total.setToolTip(
            "Rows are rounded to cents before they are added, so a rate that "
            "does not divide evenly can leave a residual."
            if total
            else ""
        )

    def _refresh_status(self) -> None:
        total = self._model.rowCount()
        visible = self._proxy.rowCount()
        noun = "account" if total == 1 else "accounts"
        if visible == total:
            self._status.setText(f"{total} {noun}")
        else:
            self._status.setText(f"{visible} of {total} {noun}")

    def _start_date(self) -> date:
        return self._from_edit.date().toPyDate()

    def _end_date(self) -> date:
        return self._to_edit.date().toPyDate()

    @staticmethod
    def _qdate(value: date) -> QDate:
        return QDate(value.year, value.month, value.day)
