"""The Ledger tab.

A read-only report, so it shares nothing with
:class:`~app.ui.pages.crud_page.CrudPage` beyond the table helpers: there is no
toolbar, no dialog, and no ``data_changed`` to emit. The tabs that do write
reload it instead.
"""

from __future__ import annotations

from datetime import date

from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import (
    QComboBox,
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
from app.domain.views import AccountView, Ledger
from app.services.ledger_service import LedgerService
from app.ui.formatting import DATE_QT_FORMAT, account_type_label, format_decimal
from app.ui.models.ledger_table_model import LedgerTableModel
from app.ui.widgets.table_view import build_filter_proxy, build_table_view

#: Notes are what wants the leftover width; the figures after them are short and
#: sized to their contents.
_STRETCH_COLUMN = 3

#: The bounds the date pair is released to before a new period is applied. Wide
#: rather than open-ended because a ``QDateEdit`` clamps to whatever it is
#: currently bounded by, and Qt's own extremes make an awkward range to read.
_MIN_DATE = QDate(1900, 1, 1)
_MAX_DATE = QDate(2999, 12, 31)


class LedgerPage(QWidget):
    """One account's postings over a chosen period, with the balance after each.

    The account is the report's subject and the period narrows it: those two
    select which postings are listed and where the running balance starts, but
    not which rows exist — an account that posted nothing in the window still
    shows the balance it opened on, so a chosen account never reads as blank.
    """

    def __init__(self, service: LedgerService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._service = service
        #: The last report read, kept so the footer and the heading can be
        #: refreshed without asking the service the same question again.
        self._ledger: Ledger | None = None
        #: The accounts behind the picker's entries, in the picker's own order.
        self._accounts: list[AccountView] = []

        self._build()
        self._prefill_period()
        self._connect()
        self.reload()

    # ------------------------------------------------------------- public API
    def reload(self) -> None:
        """Re-read the picker and the report.

        Public because the tabs that write into the ledger change what this one
        displays, and the main window calls this when any of them reports a
        change. Reading the accounts as well as the report is what keeps a
        rename or a new account from leaving the picker behind.
        """
        self._reload_accounts()
        self._reload_report()

    def show_account(self, account_id: int, start: QDate, end: QDate) -> None:
        """Open on one account and period, as the trial balance asks it to.

        Both fields move before anything is read, and every signal they would
        have emitted is held back, so a jump costs one read of the report rather
        than one per field.
        """
        self._reload_accounts()
        self._set_dates(start, end)
        self._select_account(account_id)
        self._reload_report()

    # ---------------------------------------------------------------- assembly
    def _build(self) -> None:
        self._model = LedgerTableModel()

        self._proxy = build_filter_proxy()
        self._proxy.setSourceModel(self._model)

        self._table = build_table_view(stretch_column=_STRETCH_COLUMN)
        self._table.setModel(self._proxy)

        heading = QLabel("Ledger")
        heading.setObjectName("title")

        # Which account is being read, since it is the report's subject rather
        # than a column in it.
        self._subject = QLabel()
        self._subject.setObjectName("hint")

        self._status = QLabel()
        self._status.setObjectName("hint")

        self._closing = QLabel()

        footer = QHBoxLayout()
        footer.addWidget(self._status)
        footer.addStretch(1)
        footer.addWidget(self._closing)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        layout.addWidget(heading)
        layout.addWidget(self._subject)
        layout.addWidget(self._build_controls())
        layout.addWidget(self._table, 1)
        layout.addLayout(footer)

    def _build_controls(self) -> QWidget:
        """The account picker, the period fields and the search box.

        The search is not a period filter, as on the trial balance: it narrows
        what is displayed through the proxy, while the account and the dates
        decide what the service reads.
        """
        self._account_picker = QComboBox()
        self._account_picker.setMinimumWidth(180)

        self._from_edit = self._date_edit()
        self._to_edit = self._date_edit()

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search the ledger…")
        self._search.setClearButtonEnabled(True)
        self._search.setMinimumWidth(180)

        self._refresh = QPushButton("Refresh")

        bar = QWidget()
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(QLabel("Account"))
        layout.addWidget(self._account_picker)
        layout.addWidget(QLabel("From"))
        layout.addWidget(self._from_edit)
        layout.addWidget(QLabel("To"))
        layout.addWidget(self._to_edit)
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
        # The picker's own change signal, not ``activated``: the drill-down moves
        # the index from code too, and it wants the report re-read as much as a
        # click does. Signals are blocked around every programmatic move, so
        # neither path reads twice.
        self._account_picker.currentIndexChanged.connect(self._on_account_changed)
        self._from_edit.dateChanged.connect(self._on_from_changed)
        self._to_edit.dateChanged.connect(self._on_to_changed)
        self._search.textChanged.connect(self._on_search)
        self._refresh.clicked.connect(self.reload)

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
    def _on_account_changed(self, *_: object) -> None:
        # Only the report: the picker supplies the accounts, so it cannot have
        # changed by being used.
        self._reload_report()

    def _on_from_changed(self, value: QDate) -> None:
        # Raising the start past the end is not something to refuse afterwards:
        # the end simply moves with it, so the pair is never upside down.
        self._constrain(self._to_edit, minimum=value)
        self._reload_report()

    def _on_to_changed(self, value: QDate) -> None:
        self._constrain(self._from_edit, maximum=value)
        self._reload_report()

    def _on_search(self, text: str) -> None:
        self._proxy.setFilterFixedString(text)
        self._refresh_status()

    # ------------------------------------------------------------------ helpers
    def _reload_accounts(self) -> None:
        """Refill the picker, keeping the chosen account when it is still there.

        An account the report was showing can be deleted on the accounts tab —
        it has no ledger history by then, which is the only way deletion is
        allowed — so a selection that has gone falls back to the first account
        rather than to nothing.
        """
        selected = self._selected_account_id()
        self._accounts = self._service.accounts()

        blocked = self._account_picker.blockSignals(True)
        self._account_picker.clear()
        for account in self._accounts:
            self._account_picker.addItem(account.name, account.id)
        if self._accounts:
            index = self._account_picker.findData(selected)
            self._account_picker.setCurrentIndex(index if index >= 0 else 0)
        self._account_picker.blockSignals(blocked)

    def _reload_report(self) -> None:
        """Read the report for the chosen account and period and display it."""
        account_id = self._selected_account_id()
        if account_id is None:
            # No accounts at all, which is a state to show rather than a failure
            # to report: there is nothing wrong with an empty database.
            self._ledger = None
            self._model.set_items(())
            self._refresh_subject()
            self._refresh_footer()
            self._refresh_status()
            return

        try:
            self._ledger = self._service.build(
                account_id, self._start_date(), self._end_date()
            )
        except AppError as error:
            # Deliberately narrow, as on the CRUD pages: a bug should surface
            # loudly rather than as a message box.
            QMessageBox.warning(self, "Something went wrong", str(error))
            return

        self._model.set_items(self._ledger.lines)
        self._refresh_subject()
        self._refresh_footer()
        self._refresh_status()

    def _select_account(self, account_id: int) -> None:
        """Point the picker at an account without reading the report.

        An unknown id leaves the picker where it is: the caller names an account
        it read from the report next door, and the picker was just refilled from
        the same source, so a miss is not a case that needs a fallback.
        """
        index = self._account_picker.findData(account_id)
        if index < 0:
            return
        blocked = self._account_picker.blockSignals(True)
        self._account_picker.setCurrentIndex(index)
        self._account_picker.blockSignals(blocked)

    def _set_dates(self, start: QDate, end: QDate) -> None:
        """Move both fields onto a period, reading the report neither time.

        The bounds are released before the dates move: a field still clamped by
        the other one's previous value would silently refuse a date outside it,
        so the pair is unbounded first and rebound once both have moved.
        """
        for field in (self._from_edit, self._to_edit):
            blocked = field.blockSignals(True)
            field.setMinimumDate(_MIN_DATE)
            field.setMaximumDate(_MAX_DATE)
            field.blockSignals(blocked)

        for field, value in ((self._from_edit, start), (self._to_edit, end)):
            blocked = field.blockSignals(True)
            field.setDate(value)
            field.blockSignals(blocked)

        self._bound_dates()

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

    def _refresh_subject(self) -> None:
        """Name the account being read, or say why there is none."""
        if self._ledger is None:
            self._subject.setText("No accounts yet — create one to read its ledger.")
            return
        self._subject.setText(
            f"{self._ledger.account_name} · "
            f"{account_type_label(self._ledger.account_type)} · "
            f"{self._ledger.currency_code}"
        )

    def _refresh_footer(self) -> None:
        """Show where the period leaves the account."""
        if self._ledger is None:
            self._closing.setText("")
            self._closing.setToolTip("")
            return

        self._closing.setText(
            f"Closing Balance ({self._ledger.currency_code}): "
            f"{format_decimal(self._ledger.closing_balance)}"
        )
        self._closing.setToolTip(
            "The opening balance plus every posting in the period, which is what "
            "the last row's Balance column already reads."
        )

    def _refresh_status(self) -> None:
        total = self._model.rowCount()
        visible = self._proxy.rowCount()
        noun = "line" if total == 1 else "lines"
        if visible == total:
            self._status.setText(f"{total} {noun}")
        else:
            self._status.setText(f"{visible} of {total} {noun}")

    def _selected_account_id(self) -> int | None:
        """The chosen account's id, or ``None`` when the picker has no entries."""
        data = self._account_picker.currentData()
        return data if isinstance(data, int) else None

    def _start_date(self) -> date:
        return self._from_edit.date().toPyDate()

    def _end_date(self) -> date:
        return self._to_edit.date().toPyDate()

    @staticmethod
    def _qdate(value: date) -> QDate:
        return QDate(value.year, value.month, value.day)
