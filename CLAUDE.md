# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```sh
python -m pip install -r requirements.txt   # PyQt6 is the only dependency
python main.py                              # run the app (creates data/ledger.db)
python seed.py                              # clear every table, then rewrite the seed rows
```

There is no test suite, no linter config and no build step. Python 3.9+ is required
(developed on 3.13).

`README.md` is the project's design document and explains the *why* behind most of the
rules below — read the relevant section before changing a rule it describes.

## The two commands that enforce the architecture

Both must find nothing. Run them after any change that adds an import:

```sh
grep -rEn "^\s*(from|import) (sqlite3|PyQt6)" app/domain app/services
grep -rn  "from app\.repositories"            app/ui
```

## Layers

Dependencies point one way only:

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
| `app/ui/` | Widgets, table models, dialogs, pages | `domain`, `services` |
| `main.py` | Wiring only | everything |
| `seed.py` | The sample rows, run on startup and on demand | `app` layers |

Services depend on the `Protocol`s in `app/repositories/interfaces.py`, never on the
concrete `Sqlite*Repository` classes. Only `main.py` and `seed.py` import a repository.

## Adding an entity — the path through every layer

1. `app/domain/<entity>.py` — dataclass with `id: int | None = None` **last**, plus a
   `validate()` for rules intrinsic to the entity.
2. `app/repositories/interfaces.py` — add the port(s), widening only as far as the
   services actually call.
3. `app/repositories/<entity>_repository.py` — subclass `SqliteRepository`, declaring
   `table` and `columns` and implementing `_to_entity` / `_to_parameters`.
4. `app/core/schema.py` — add the `CREATE TABLE IF NOT EXISTS` statement to
   `TABLE_STATEMENTS` (and indexes to `INDEX_STATEMENTS`).
5. `app/services/<entity>_service.py` — validation needing a second entity, plus
   `validate()` exposed publicly for the dialog.
6. `app/ui/models/<entity>_table_model.py` — subclass `BaseTableModel`, declare
   `headers` and `display()`.
7. `app/ui/dialogs/<entity>_dialog.py` — an ordinary `QDialog` built with the helpers in
   `form_support.py`.
8. `app/ui/pages/<entity>_page.py` — subclass `CrudPage` and implement only `_prompt`,
   `_remove`, `_describe` (plus `_delete_refusal` if deletes can be blocked).
9. Wire it in `main.py`, add the tab and `data_changed` connections in
   `app/ui/main_window.py`, and add the rows to `seed.py` if the seed needs them.

## Architecture notes that are easy to get wrong

**One generic repository.** `SqliteRepository` writes all CRUD SQL; a subclass supplies
`table`, `columns` and the two mappings. `add`/`update` stamp the generated id with
`dataclasses.replace`, so entities must be dataclasses with an `id` attribute.

**An entity that owns child rows overrides `_write_owned_rows(cursor, entity)`.** It runs
inside the one transaction the base already opened — `Database.transaction` is deliberately
*not* re-entrant, so a child repository must never open its own. There is no delete
counterpart: children carry `ON DELETE CASCADE`. `SqliteTransactionRepository` replaces its
splits wholesale there, which is why one hook works for both insert and update.

**Validation has one home.** Rules intrinsic to an entity live on `Entity.validate()`
(called by the service, and by the dialog before it closes); rules needing a second entity
live in the service. `ValidationError` carries a `field=` kwarg — `report_validation_error`
uses it to focus the offending widget. Wrap user-facing failures in `AppError`
subclasses: the UI catches `AppError` only, so a fixable problem must not raise anything
else.

**Money is `Decimal` over `TEXT`, never SQL arithmetic.** `currencies.rate`,
`transactions.amount` and `splits.amount` are `TEXT` holding `str(Decimal)` and read back
with `Decimal(text)`. SQLite's `SUM` would coerce to `REAL` and lose the precision the
column type exists to preserve, so aggregation happens in Python — see
`SqliteTransactionRepository.net_by_account`.

**`DATETIME_FORMAT` is defined once**, in
[transaction_repository.py](app/repositories/transaction_repository.py) as
`"%Y-%m-%d %H:%M"`. `app/ui/formatting.py` must keep rendering that same shape. The format
is zero-padded so text comparison is chronological — `net_by_account` and `date_bounds`
rely on it.

**Signs, not column order, say which side is the debit.** `Transaction.splits()` is the
single definition of how a type posts: each side takes the sign its `TransactionType`
gives it — for a payment the counterparty debited and the cash account credited, for a
receipt the mirror image — always summing to zero. The sign lives on the enum member, so
a new type states its direction rather than inheriting one. The repository writes exactly
what `splits()` returns and never re-derives the direction. Direction follows from the
transaction's `type`, not from a form field.

**A refused action is disabled, not just rejected.** `CrudPage._delete_refusal(item)`
returns the reason a row cannot be deleted; the page turns that into a disabled Delete
button carrying the reason as a tooltip. Presentation only — the rule still lives in the
service, with a RESTRICT foreign key underneath it as the backstop.

**Schema changes to an existing table need an entry in `COLUMN_ADDITIONS`.** The tuples are
`(table, column, add-statement)` and `Database.connect` runs one only when the column is
missing, which is what keeps `CREATE TABLE IF NOT EXISTS` from silently leaving old
databases behind. `COLUMN_ADDITIONS` runs *between* the tables and the indexes, because an
index may name a column only these add. `ALTER TABLE` cannot add a `CHECK`, and SQLite
cannot alter one — widening a `CHECK`-constrained enum (e.g. `TransactionType`) means
rebuilding the table, not adding a row here. That is why adding `receipt` shipped as an
edit to `TRANSACTIONS_TABLE` plus a re-seed, rather than an entry in this tuple.

**`PRAGMA foreign_keys = ON`** is set per connection in `Database.connect`; SQLite defaults
it off, so removing it silently disables every RESTRICT.

**The base currency is a fact about the set, not a row preference.** Exactly one row has
`is_base = 1`, held by a partial unique index (`WHERE is_base = 1`). It has a fixed rate
(`BASE_RATE`) and method (`mul`) that `Currency.validate` refuses to change, cannot be
deleted by anything except `seed.py`'s `allow_base=True`, and is not a field any dialog
offers.

**A read-only tab is not a CRUD tab.** `TrialBalancePage` does not extend `CrudPage` — it
shares only `build_table_view` / `build_filter_proxy` and `BaseTableModel`, and reloads
from the other pages' `data_changed` signal. A page that writes emits `data_changed`;
`MainWindow` wires which tabs each one refreshes, always in the direction of the reader.

**Cross-entity deletes are refused, not cascaded**, when the child was not the user's to
lose: `CurrencyService` counts accounts, `AccountService.delete_refusal` counts
transactions, and each names the count in the message.

## UI conventions

- `app/ui/theme.py` applies `Fusion` + an explicit light `QPalette` + a stylesheet. The
  native Windows 11 style follows the OS dark-mode setting and ignores QSS, so this stays.
- Search is free: `build_filter_proxy()` returns a `QSortFilterProxyModel` with
  `setFilterKeyColumn(-1)`, matching every column case-insensitively. Selection rows are in
  *proxy* coordinates — map with `mapToSource` before touching the model.
- Pages talk to services only; dialogs re-read their lookup lists (currencies, accounts) on
  every open so a picker cannot go stale.
- A column's renderers in a table model must match `headers` in length and order.
- Account names in the seed are Arabic (`الصندوق`, `المصروفات`) and the Windows console
  cannot encode them — `seed.py` prints ASCII only.

## Style

Comments and docstrings explain *why* a decision was made, not what the code does; they are
substantial and close to the code they justify. Match that density. Keep identifiers,
comments and docstrings in English. The database is disposable — `data/` is gitignored and
any change to the schema is expected to be re-seeded rather than migrated by hand.


# Instructions

Always:
- Use clean code priciples, SOLID, DRY, etc ...
- Ask me for details.
