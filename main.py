"""Entry point and composition root.

Every concrete class is built here and injected downwards. This module and
``seed.py`` are the only two that import a repository — which is what keeps the
dependencies between layers pointing in a single direction.
"""

from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication, QMessageBox

from app.config import APP_NAME, DEFAULT_DATABASE_PATH
from app.core.database import Database
from app.domain.errors import AppError
from app.repositories.account_repository import SqliteAccountRepository
from app.repositories.currency_repository import SqliteCurrencyRepository
from app.services.account_service import AccountService
from app.services.currency_service import CurrencyService
from app.ui.main_window import MainWindow
from app.ui.theme import apply_light_theme
from seed import seed_if_empty


def main() -> int:
    """Wire the application up and run it. Returns the process exit code."""
    # The QApplication comes first so a failure below can be reported in a
    # dialog rather than only on a console the user may never see.
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    apply_light_theme(app)

    database = Database(DEFAULT_DATABASE_PATH)
    try:
        database.connect()
    except AppError as error:
        QMessageBox.critical(None, APP_NAME, f"Could not open the database.\n\n{error}")
        return 1

    try:
        currency_repository = SqliteCurrencyRepository(database)
        account_repository = SqliteAccountRepository(database)

        currency_service = CurrencyService(currency_repository, account_repository)
        account_service = AccountService(account_repository, currency_repository)

        # First run, or a database the user emptied: without this the app opens
        # on two blank tables. Only ever inserts, so it cannot discard data.
        try:
            seed_if_empty(currency_service, account_service)
        except AppError as error:
            # Not fatal: empty tables are a working application. Report it and
            # carry on, rather than refusing to start over sample data.
            QMessageBox.warning(
                None, APP_NAME, f"Could not write the sample data.\n\n{error}"
            )

        window = MainWindow(currency_service, account_service, database.path)
        window.show()
        return app.exec()
    finally:
        database.close()


if __name__ == "__main__":
    sys.exit(main())
