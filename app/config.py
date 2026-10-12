"""Application-wide constants and filesystem paths."""

from __future__ import annotations

from pathlib import Path

APP_NAME = "Ledger"

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# The database lives next to the code rather than in the package, so it survives
# a reinstall and is obvious to find.
DATA_DIR = PROJECT_ROOT / "data"
DEFAULT_DATABASE_PATH = DATA_DIR / "ledger.db"
