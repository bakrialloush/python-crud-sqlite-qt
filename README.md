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
| `is_base` — `0`, `1` | |

`rate` and `method` describe a conversion: `method=mul` means an amount is
multiplied by the rate, `method=div` means it is divided by it. Rates are held as
`decimal.Decimal` and stored as `TEXT` — SQLite has no `DECIMAL` type, and a
binary float would corrupt money values.

`is_base` marks the currency the other rates are quoted against. There is
exactly one, the seed sets it, and it is not a field the form offers: being the
base is a fact about the set rather than a preference about one row. It also
fixes its own rate and method — converting an amount into the base is the
identity — so those two arrive locked on the edit form and are refused by
`Currency.validate` for any other caller. The base cannot be deleted; every
other rate would be left quoting a currency that is not there. Both rules sit in
the service and the entity, with a partial unique index (`WHERE is_base = 1`)
holding the one-base rule underneath them.

## Running it

```sh
python -m pip install -r requirements.txt
python main.py
```

Requires Python 3.9 or newer. The database is created on first run at
`data/ledger.db`, next to the code. Delete that file to start over.

## Seeding it

The app populates itself on startup: a database that holds no currencies *and*
no accounts — a missing file, or one the user emptied — gets the seed rows before
the window opens, so it never comes up on two blank tables. Once anything is
stored, it is left alone; the check is per database rather than per table, so
deleting the seed account does not bring it back on the next launch.

```sh
python seed.py
```

does the same thing on demand, but clears both tables first — so it is safe to
re-run and always leaves the same two rows, with the same ids. Run it when you
want the sample data back, not merely when it is missing.

Either way you get one currency (`USD`, rate `1`, `mul`, the base) and one asset
account, `الصندوق`, denominated in it, written through the services rather than
raw SQL — so the seed faces the same validation the UI does. Treat the database
as disposable.

The database from an older version gains the `is_base` column when it is next
opened, but as `0`: no existing row is promoted to base, since which currency
the rates were quoted against is not something the application can infer. Run
`python seed.py` to get the seed back with its base flag.

## Layers

Dependencies point in one direction only:

```
main.py, seed.py  (composition roots)
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
| `seed.py` | The sample rows, written on startup and on demand | `app` layers |

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
connection, since SQLite defaults it off per connection. The base currency is
refused the same way, and for the same reason: it is referred to by every other
rate rather than by a row.

**A refused action is disabled, not just rejected.** `CrudPage` hands each row
to `_delete_refusal`, which returns the reason it cannot be deleted. The page
turns a reason into a disabled Delete button carrying it as a tooltip, so the
rule reaches the user before they act rather than in a message box afterwards.
It is presentation only — `_delete_refusal` decides nothing the service does not
already decide.

**A column added later carries its own migration.** `CREATE TABLE IF NOT EXISTS`
leaves an existing table untouched, so `schema.py` also lists the statements
that add columns to tables that already exist, and `Database.connect` runs each
one only when its column is missing. That keeps startup idempotent without
version tracking, and keeps an older database usable instead of failing on a
column it never had.

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
- The base currency keeps its rate and method, and cannot be deleted
