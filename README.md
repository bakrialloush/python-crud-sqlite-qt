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
| `type` — `payment`, `receipt` | `account_id` → `accounts.id` |
| `cash_account_id` → `accounts.id` | `amount` — signed, `+` debit `−` credit |
| `account_id` → `accounts.id` | |
| `amount` | |
| `notes` | |

A **transaction** moves money between a cash account and one other, and there
are two kinds of it. A **payment** takes money out of the cash account and posts
it to the counterparty: the counterparty is debited `+amount` and the cash
account credited `−amount`. A **receipt** is the mirror image — money in, so the
cash account is debited and the counterparty credited. Either is not one row: it
is a double-entry posting, stored as one `transactions` row plus exactly two
`splits`, which always sum to zero. The sign carries the direction, so nothing
depends on the order the rows come back in. Direction is not a field on the
form: it follows from the transaction's `type`, so the two kinds cannot disagree
about which side is the debit — which is why the Payments and Receipts tabs
share one form and one table.

`account_id` is the counterparty — the account paid for a payment, the account
received from for a receipt — so it is named for the side it holds rather than
for one direction.

A transaction moves money rather than converting it, so both of its accounts
have to be held in the same currency. The picker only offers accounts that are,
and the service refuses anything else, rather than pricing the posting with a
rate.

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

A **trial balance** reports every account's position over a period. An account's
figure is nothing but the sum of the splits posted to it — debits positive,
credits negative — so the report reads the ledger the transactions wrote rather
than keeping a balance of its own. Accounts may be held in more than one currency, so
each row carries its own figure *and* a second one converted into the base: the
converted column is what the footer totals, since adding amounts in different
currencies would mean nothing. Converting into the base is the inverse of a
currency's rate (`mul` by a rate is undone by dividing by it), and each converted
figure is rounded to cents before it is added, so what the footer sums is what
the table shows.

A **ledger** reports one account over a period: every posting to it, oldest
first, with the balance after each. Where the trial balance shows the total a
period left an account holding, the ledger shows the postings that total came
from — and, since a period read on its own starts mid-history, the balance the
account carried into it. That opening figure is the report's first line rather
than a note beside it: a running balance has to start somewhere the reader can
see, and an account that posted nothing in the window still has a position. It
is a position rather than a movement, which is why it leaves the Debit and Credit
columns blank and appears only in Balance — put in a column it would be counted
twice, and those two columns are read as the period's movement. Reading one
account at a time is also why the ledger needs no base currency: it reports in
the account's own.

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
`المصروفات`. Two rather than one because a transaction moves money between two
accounts, so with the till alone there would be nothing to pay or receive and
the Payments and Receipts tabs would be inert on a fresh install. Both are
written through the services rather than raw SQL — so the seed faces the same
validation the UI does. Treat the database as disposable.

The database from an older version gains the `is_base` column when it is next
opened, but as `0`: no existing row is promoted to base, since which currency
the rates were quoted against is not something the application can infer. Run
`python seed.py` to get the seed back with its base flag.

A database from before payments existed gains the `transactions` and `splits`
tables the same way, and needs nothing else — both are new tables, so
`CREATE TABLE IF NOT EXISTS` adds them on the next launch and no existing row is
touched.

A database from before *receipts* existed is the other case, and is not upgraded
in place: the `type` CHECK was widened from `('payment')` to
`('payment', 'receipt')`, and `payment_account_id` was renamed to `account_id`.
SQLite cannot alter a CHECK, so — as with any schema change here — delete
`data/ledger.db` and let the app re-seed it.

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

**Money is added in Python, not in SQL.** `splits.amount` is `TEXT` holding an
exact `Decimal`, so SQLite's `SUM` would coerce it to a `REAL` and lose the
precision the column type exists to preserve. The trial balance's repository
method filters the rows by date and the walk over them adds `Decimal` to
`Decimal`, which is why the report can be trusted to the cent.

**A read-only tab is not a CRUD tab.** Neither report has a toolbar, a dialog or
anything to write, so neither extends `CrudPage` — they share only the table
helpers (`build_table_view`, `build_filter_proxy`) and the table model base, and
the pages that *do* write reload them through their `data_changed` signal. A
report's period filter and its search box stay independent: the dates decide what
the service reads, the search decides what the proxy displays. A report may also
*report* what was opened rather than acting on it — the trial balance emits the
account a double-click landed on and `MainWindow`, which owns both tabs and knows
which one is showing, makes the jump into the ledger.

**A report's period has one definition.** `app/services/period.py` turns the two
days a report is asked for into the instants it reads, inclusive at both ends;
both reports delegate to it rather than deriving the last instant of a day each.
The running balance is the same kind of shared decision kept in one place: the
ledger adds each posting's `Decimal` in Python, as the trial balance does, and
carries the total forward from the opening balance — which is what makes its last
row's balance the closing one by construction rather than by a second addition
that could drift from it.

**A light theme that stays light.** `Fusion` plus an explicit `QPalette` plus a
stylesheet. The native Windows 11 style follows the operating system's
dark-mode setting and ignores much of QSS, so the app would otherwise come up
dark for anyone running Windows in dark mode.

## Features

- Full create, read, update and delete for currencies, accounts, payments and
  receipts
- Live search across every column, case-insensitive
- Duplicate currency codes rejected, case-insensitively (`usd` collides with `USD`)
- Rates validated as positive, finite decimals
- Accounts cannot be saved without a currency; currencies cannot be deleted while in use
- The base currency keeps its rate and method, and cannot be deleted
- Payments and Receipts tabs share one form and one table: a payment posts the
  counterparty debit / cash credit, a receipt the mirror image, and the
  direction lives on the transaction type rather than in the form
- Every transaction — payment or receipt — is a balanced double-entry posting,
  its two splits written with it in one database transaction and rewritten when
  it is edited
- A transaction's cash side is restricted to asset accounts, and both of its
  accounts to one currency — enforced in the service, not only in the picker
- Deleting an account a transaction posted to is refused, with the reason on the
  disabled button rather than in a message box afterwards
- A Trial Balance tab: every account's net position over a date range, shown in
  its own currency with an `In Base` column, orderable by account type, with a
  hide-zero-balances toggle and live search
- A Ledger tab: one account's postings over a date range, oldest first, with the
  balance after each and the opening balance the period starts from — reachable
  by double-clicking an account in the Trial Balance, which opens it on the same
  period
