"""The service layer: use cases and the rules that span more than one entity.

Services depend on the Protocols in :mod:`app.repositories.interfaces`, never on
a concrete repository, and import neither ``sqlite3`` nor ``PyQt6``.
"""
