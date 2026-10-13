"""The application shell."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import QMainWindow, QTabWidget, QWidget

from app.config import APP_NAME
from app.domain.enums import TransactionType
from app.services.account_service import AccountService
from app.services.currency_service import CurrencyService
from app.services.ledger_service import LedgerService
from app.services.transaction_service import TransactionService
from app.services.trial_balance_service import TrialBalanceService
from app.ui.pages.account_page import AccountPage
from app.ui.pages.currency_page import CurrencyPage
from app.ui.pages.ledger_page import LedgerPage
from app.ui.pages.transaction_page import TransactionPage
from app.ui.pages.trial_balance_page import TrialBalancePage


class MainWindow(QMainWindow):
    """Hosts one tab per entity and keeps their views consistent."""

    def __init__(
        self,
        currency_service: CurrencyService,
        account_service: AccountService,
        transaction_service: TransactionService,
        trial_balance_service: TrialBalanceService,
        ledger_service: LedgerService,
        database_path: Path,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(APP_NAME)
        self.resize(940, 620)

        self._currency_page = CurrencyPage(currency_service, parent=self)
        self._account_page = AccountPage(account_service, parent=self)
        # The two transaction tabs are the same page class, told which way the
        # money moves. The type supplies the headings, the field labels and the
        # direction the splits post in.
        self._payment_page = TransactionPage(
            transaction_service, TransactionType.PAYMENT, parent=self
        )
        self._receipt_page = TransactionPage(
            transaction_service, TransactionType.RECEIPT, parent=self
        )
        self._trial_balance_page = TrialBalancePage(trial_balance_service, parent=self)
        self._ledger_page = LedgerPage(ledger_service, parent=self)

        self._tabs = QTabWidget()
        self._tabs.addTab(self._currency_page, "Currencies")
        self._tabs.addTab(self._account_page, "Accounts")
        self._tabs.addTab(self._payment_page, "Payments")
        self._tabs.addTab(self._receipt_page, "Receipts")
        self._tabs.addTab(self._trial_balance_page, "Trial Balance")
        self._tabs.addTab(self._ledger_page, "Ledger")
        self.setCentralWidget(self._tabs)

        # The accounts table shows each account's currency code and name, so
        # editing a currency has to refresh it. The other direction needs no
        # wiring: the account dialog re-reads the currencies when it opens.
        self._currency_page.data_changed.connect(self._account_page.reload)
        # Both transaction tables name their two accounts, so renaming one has
        # to reach them. That way round only: their dialog re-reads the accounts
        # when it opens, and the accounts table shows no totals.
        for page in (self._payment_page, self._receipt_page):
            self._account_page.data_changed.connect(page.reload)
        # The reports read accounts, their currencies and their postings, so a
        # change on any of the four tabs moves them. That way round only: they
        # are read-only, so neither has a ``data_changed`` of its own to emit.
        for page in (
            self._currency_page,
            self._account_page,
            self._payment_page,
            self._receipt_page,
        ):
            page.data_changed.connect(self._trial_balance_page.reload)
            page.data_changed.connect(self._ledger_page.reload)

        # Opening a row in the trial balance reads that account's ledger, which
        # makes the report that totals a way into the one that details. The jump
        # is the window's to make because the window owns both tabs — and which
        # of them is showing.
        self._trial_balance_page.account_activated.connect(self._open_ledger)

        self.statusBar().showMessage(f"Database: {database_path}")

    def _open_ledger(self, account_id: int, start: QDate, end: QDate) -> None:
        """Show the ledger on one account and period, and bring it to the front."""
        self._ledger_page.show_account(account_id, start, end)
        self._tabs.setCurrentWidget(self._ledger_page)
