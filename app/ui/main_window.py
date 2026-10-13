"""The application shell."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtWidgets import QMainWindow, QTabWidget, QWidget

from app.config import APP_NAME
from app.domain.enums import TransactionType
from app.services.account_service import AccountService
from app.services.currency_service import CurrencyService
from app.services.transaction_service import TransactionService
from app.services.trial_balance_service import TrialBalanceService
from app.ui.pages.account_page import AccountPage
from app.ui.pages.currency_page import CurrencyPage
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

        tabs = QTabWidget()
        tabs.addTab(self._currency_page, "Currencies")
        tabs.addTab(self._account_page, "Accounts")
        tabs.addTab(self._payment_page, "Payments")
        tabs.addTab(self._receipt_page, "Receipts")
        tabs.addTab(self._trial_balance_page, "Trial Balance")
        self.setCentralWidget(tabs)

        # The accounts table shows each account's currency code and name, so
        # editing a currency has to refresh it. The other direction needs no
        # wiring: the account dialog re-reads the currencies when it opens.
        self._currency_page.data_changed.connect(self._account_page.reload)
        # Both transaction tables name their two accounts, so renaming one has
        # to reach them. That way round only: their dialog re-reads the accounts
        # when it opens, and the accounts table shows no totals.
        for page in (self._payment_page, self._receipt_page):
            self._account_page.data_changed.connect(page.reload)
        # The report reads accounts, their currencies and their postings, so a
        # change on any of the four tabs moves it. That way round only: it is
        # read-only, so it has no ``data_changed`` of its own to emit.
        for page in (
            self._currency_page,
            self._account_page,
            self._payment_page,
            self._receipt_page,
        ):
            page.data_changed.connect(self._trial_balance_page.reload)

        self.statusBar().showMessage(f"Database: {database_path}")
