"""The application error hierarchy.

Every error the application raises deliberately descends from :class:`AppError`.
That gives the presentation layer one thing to catch: the difference between a
problem the user can act on and a genuine bug, which should surface loudly
instead of being swallowed by a message box.
"""

from __future__ import annotations


class AppError(Exception):
    """Base class for expected, user-presentable application errors."""


class ValidationError(AppError):
    """A domain invariant or business rule was violated.

    ``field`` names the offending form field, when there is one, so a dialog can
    put the cursor somewhere useful.
    """

    def __init__(self, message: str, field: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.field = field


class NotFoundError(AppError):
    """A requested entity does not exist."""


class ReferentialIntegrityError(AppError):
    """The operation was refused because other records still reference the target."""


class PersistenceError(AppError):
    """The underlying store failed. Raised at the repository boundary."""


class ConstraintViolation(PersistenceError):
    """A database constraint refused the operation.

    This is the last line of defence: services check the rules first, and a
    constraint firing means a check was bypassed or lost a race.
    """
