"""Ledger — a small PyQt6 + SQLite CRUD application.

Layers, from the inside out:

``domain``        entities, enums, validation rules. Imports nothing but the standard library.
``services``      use cases and the rules that span more than one entity.
``repositories``  every SQL statement, plus the ports the services depend on.
``core``          the SQLite connection and schema.
``ui``            PyQt6 widgets. Talks to services, never to the database.
"""
