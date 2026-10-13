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

and one that moves money between them:

| Transaction | Split |
| --- | --- |
| `id` | `id` |
| `datetime` | `transaction_id` → `transactions.id` |
| `type` — `payment` | `account_id` → `accounts.id` |
| `cash_account_id` → `accounts.id` | `amount` — signed, `+` debit `−` credit |
| `payment_account_id` → `accounts.id` | |
| `amount` | |
| `notes` | |

A **payment** takes money out of a cash account and posts it to the account being
paid. It is not one row: it is a double-entry posting, stored as one
`transactions` row plus exactly two `splits` — the account being paid debited
`+amount`, the cash account credited `−amount` — which always sum to zero. The
sign carries the direction, so nothing depends on the order the rows come back
in. Direction is not a field on the form: it follows from the transaction's
`type`, so a second type added later cannot disagree with the first about which
side is the debit.

A payment moves money rather than converting it, so both of its accounts have to
be held in the same currency. The picker only offers accounts that are, and the
service refuses anything else, rather than pricing the posting with a rate.

`rate` and `method` describe a conversion: `method=mul` means an amount is
multiplied by the rate, `method=div` means it is divided by it. Rates are held as
`decimal.Decimal` and stored as `TEXT` — SQLite has no `DECIMAL` type, and a
binary float would corrupt money values. Amounts are stored the same way, for the
same reason.

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

The app populates itself on startup: a database that holds no currencies, no
accounts *and* no transactions — a missing file, or one the user emptied — gets
the seed rows before the window opens, so it never comes up on blank tables. Once
anything is stored, it is left alone; the check is per database rather than per
table, so deleting the seed account does not bring it back on the next launch.

```sh
python seed.py
```

does the same thing on demand, but clears every table first — so it is safe to
re-run and always leaves the same rows, with the same ids. Run it when you want
the sample data back, not merely when it is missing.

Either way you get one currency (`USD`, rate `1`, `mul`, the base) and two
accounts denominated in it: an asset account, `الصندوق`, and an expense account,
`المصروفات`. Two rather than one because a payment moves money between two
accounts, so with the till alone there would be nothing to pay and the Payments
tab would be inert on a fresh install. Both are written through the services
rather than raw SQL — so the seed faces the same validation the UI does. Treat
the database as disposable.

The database from an older version gains the `is_base` column when it is next
opened, but as `0`: no existing row is promoted to base, since which currency
the rates were quoted against is not something the application can infer. Run
`python seed.py` to get the seed back with its base flag.

A database from before payments existed gains the `transactions` and `splits`
tables the same way, and needs nothing else — both are new tables, so
`CREATE TABLE IF NOT EXISTS` adds them on the next launch and no existing row is
touched.

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

**An entity that owns rows says so in one hook.** A transaction is one row here
and two in `splits`, and the three have to be written together or not at all —
but each `add`/`update` already opens the only transaction SQLite allows, so a
second repository cannot open its own. Rather than make `Database.transaction`
re-entrant with savepoints, which would weaken a guarantee the whole data layer
rests on, the base class gained `_write_owned_rows`, called inside the
transaction it has already opened. It does nothing by default, so no other
repository changed. Deletion needs no counterpart: the splits carry
`ON DELETE CASCADE` and the database removes them with the row.

**Validation has one home.** Rules intrinsic to an entity live on it
(`Currency.validate`). Rules that need a second entity — is this code taken, does
this currency still have accounts — live in the service. Services expose
`validate()` publicly so the dialogs can run the real rules *before* closing,
which means the user reads the error with the form still in front of them.
`Transaction.splits()` is where the posting is defined, and the repository writes
exactly what it returns: neither re-derives which side is the debit.

**Deleting a currency that accounts use is blocked, not cascaded.** Silently
removing it would destroy accounts the user never asked to touch. The service
gives a message naming how many accounts block it, and an
`ON DELETE RESTRICT` foreign key is the backstop that holds the line even for a
caller that bypasses the service. `PRAGMA foreign_keys = ON` is set on every
connection, since SQLite defaults it off per connection. The base currency is
refused the same way, and for the same reason: it is referred to by every other
rate rather than by a row. An account is refused by the same rule one level down
— deleting one a payment posted to would take ledger history with it, so
`AccountService.delete_refusal` names how many payments block it, the page
disables the button with that reason as its tooltip, and the RESTRICT foreign key
on both of the transaction's account columns holds the line underneath.

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

- Full create, read, update and delete for currencies, accounts and payments
- Live search across every column, case-insensitive
- Duplicate currency codes rejected, case-insensitively (`usd` collides with `USD`)
- Rates validated as positive, finite decimals
- Accounts cannot be saved without a currency; currencies cannot be deleted while in use
- The base currency keeps its rate and method, and cannot be deleted
- Every payment is a balanced double-entry posting, its two splits written with
  it in one database transaction and rewritten when it is edited
- A payment's cash side is restricted to asset accounts, and both of its accounts
  to one currency — enforced in the service, not only in the picker
- Deleting an account a payment posted to is refused, with the reason on the
  disabled button rather than in a message box afterwards
