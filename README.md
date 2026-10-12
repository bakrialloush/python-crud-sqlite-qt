# Ledger

A small desktop CRUD application built with **PyQt6** and **SQLite**, covering two
related models:

| Currency | Account |
| --- | --- |
| `id` | `id` |
| `name` | `name` |
| `code` | `currency_id` → `currencies.id` |
| `rate` | `type` — `asset`, `liability`, `equity`, `revenue`, `expense` |
| `method` — `mul`, `div` | |

`rate` and `method` describe a conversion: `method=mul` means an amount is
multiplied by the rate, `method=div` means it is divided by it. Rates are held as
`decimal.Decimal` and stored as `TEXT` — SQLite has no `DECIMAL` type, and a
binary float would corrupt money values.

## Running it

```sh
python -m pip install -r requirements.txt
python main.py
```

Requires Python 3.9 or newer. The database is created on first run at
`data/ledger.db`, next to the code. Delete that file to start over.

## Layers

Dependencies point in one direction only:

```
main.py  (composition root)
   │
   ├─> ui/ ──────────> services/ ──> repositories/interfaces.py   (Protocols)
   │                      │                    ▲
   │                      └─> domain/          │ implemented by
   │                                          │
   └─> core/database.py ────────> repositories/sqlite_repository.py
```

| Package | Responsibility | May import |
| --- | --- | --- |
| `app/domain/` | Entities, enums, validation rules, errors | standard library only |
| `app/services/` | Use cases and rules spanning more than one entity | `domain` |
| `app/repositories/` | Every SQL statement. `interfaces.py` holds the ports | `domain`, `core` |
| `app/core/` | SQLite connection, pragmas, schema | `domain.errors` |
| `app/ui/` | Widgets, table models, dialogs | `domain`, `services` |
| `main.py` | Wiring only | everything |

The rule that makes the separation real, and which these two commands confirm —
both must find nothing:

```sh
grep -rEn "^\s*(from|import) (sqlite3|PyQt6)" app/domain app/services
grep -rn  "from app\.repositories"            app/ui
```

(The patterns match imports specifically. The packages do *mention* both names
in their docstrings, which is the point of the rule.)

So the business rules can be read and reasoned about without a database or a
running event loop.

## Design notes

**One generic repository.** `SqliteRepository` writes the CRUD statements once;
a subclass supplies its table name, column list, and the two row/entity
mappings. Adding an entity is a new subclass and no edits to existing code.

**Validation has one home.** Rules intrinsic to an entity live on it
(`Currency.validate`). Rules that need a second entity — is this code taken, does
this currency still have accounts — live in the service. Services expose
`validate()` publicly so the dialogs can run the real rules *before* closing,
which means the user reads the error with the form still in front of them.

**Deleting a currency that accounts use is blocked, not cascaded.** Silently
removing it would destroy accounts the user never asked to touch. The service
gives a message naming how many accounts block it, and an
`ON DELETE RESTRICT` foreign key is the backstop that holds the line even for a
caller that bypasses the service. `PRAGMA foreign_keys = ON` is set on every
connection, since SQLite defaults it off per connection.

**Search needs no subclass.** `QSortFilterProxyModel` with
`setFilterKeyColumn(-1)` already matches every column's display text,
case-insensitively.

**A light theme that stays light.** `Fusion` plus an explicit `QPalette` plus a
stylesheet. The native Windows 11 style follows the operating system's
dark-mode setting and ignores much of QSS, so the app would otherwise come up
dark for anyone running Windows in dark mode.

## Features

- Full create, read, update and delete for currencies and accounts
- Live search across every column, case-insensitive
- Duplicate currency codes rejected, case-insensitively (`usd` collides with `USD`)
- Rates validated as positive, finite decimals
- Accounts cannot be saved without a currency; currencies cannot be deleted while in use
