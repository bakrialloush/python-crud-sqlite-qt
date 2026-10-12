"""The domain layer: entities, enums, validation and errors.

Nothing in this package may import ``sqlite3`` or ``PyQt6``. Keeping it that way
is what lets the business rules be reasoned about — and exercised — without a
database or a running event loop.
"""
