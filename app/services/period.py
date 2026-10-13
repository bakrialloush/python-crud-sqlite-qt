"""The period a report reads over, defined once.

A report is asked for a range of days and reads a range of instants, and turning
one into the other is a decision rather than an arithmetic detail: a period is
inclusive at both ends, so its last day has to become the last instant *of* that
day — not its first, and not the following midnight. Two reports deriving that
separately is exactly how one of them ends up quietly dropping the final day's
transactions, so it lives here and every report delegates to it.
"""

from __future__ import annotations

from datetime import date
from datetime import datetime as DateTime
from datetime import time

from app.repositories.interfaces import TransactionRepository


def start_of(day: date) -> DateTime:
    """The first instant of ``day``."""
    return DateTime.combine(day, time.min)


def end_of(day: date) -> DateTime:
    """The last instant of ``day``, so the whole of it counts."""
    return DateTime.combine(day, time.max)


def transaction_period(
    transactions: TransactionRepository,
) -> tuple[date, date] | None:
    """The days the stored transactions span, or ``None`` when there are none.

    For prefilling a report's date fields, so it opens on the period the data
    covers instead of one the reader has to discover first.
    """
    bounds = transactions.date_bounds()
    if bounds is None:
        return None
    return (bounds[0].date(), bounds[1].date())
