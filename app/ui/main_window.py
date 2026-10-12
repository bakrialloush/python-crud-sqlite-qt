"""The application shell."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtWidgets import QMainWindow, QTabWidget, QWidget

from app.config import APP_NAME
from app.services.account_service import AccountService
from app.services.currency_service import CurrencyService
from app.ui.pages.account_page import AccountPage
from app.ui.pages.currency_page import CurrencyPage


class MainWindow(QMainWindow):
    """Hosts one tab per entity and keeps their views consistent."""

    def __init__(
        self,
        currency_service: CurrencyService,
        account_service: AccountService,
        database_path: Path,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(APP_NAME)
        self.resize(940, 620)

        self._currency_page = CurrencyPage(currency_service, parent=self)
        self._account_page = AccountPage(account_service, parent=self)

        tabs = QTabWidget()
        tabs.addTab(self._currency_page, "Currencies")
        tabs.addTab(self._account_page, "Accounts")
        self.setCentralWidget(tabs)

        # The accounts table shows each account's currency code and name, so
        # editing a currency has to refresh it. The other direction needs no
        # wiring: the account dialog re-reads the currencies when it opens.
        self._currency_page.data_changed.connect(self._account_page.reload)

        self.statusBar().showMessage(f"Database: {database_path}")
