# SyntheticWorkplace

SyntheticWorkplace generates a fictional organisation for safe agent training and evaluation. Its emails, CRM, invoices, line-item spreadsheets, support tickets, and internal documents are built together so references resolve across the dataset.

## Quickstart

Use Python 3.10 or newer. Runtime code uses only the Python standard library and runs on CPU.

```powershell
python -m pip install -e .
python -m synthwork generate --seed 42 --out .\sample-org
python -m synthwork validate .\sample-org
python -m synthwork query --data .\sample-org --type all --q "delivery schedule"
python -m synthwork stats .\sample-org
```

The same integer seed and profile produce byte-identical files on every run. Seeds are integers from 0 through 4294967295. A different seed changes the company and generated records. File ordering, JSON key ordering, timestamps, identifiers, and CSV line endings are stable. The `generate` command also reports measured elapsed time. `stats` reports a deterministic workload estimate so its output does not change with machine speed or run timing.

Available volume profiles are `demo` and `scale`. The `fixture` profile is a small profile used by the checked-in test corpus.

## Architecture

```text
integer seed + volume profile
              |
              v
     seeded local generator
              |
      +-------+--------+
      |        |        |
      v        v        v
   company   people   CRM records
                       |
             +---------+----------+
             |         |          |
             v         v          v
          email      invoices   documents
          threads       |       reference IDs
             |          v
             |     CSV line items
             v
          tickets
             |
             v
     reference_graph.json
             |
       +-----+------+
       |            |
       v            v
   validator    ranked query
                    |
                    v
                 stats
```

The generator creates target entities first, then writes references using their generated IDs. `reference_graph.json` is an inspectable edge list. Validation independently checks the record fields, so an incomplete graph cannot hide a broken reference.

## HONESTY BOUNDARY

ALL data is synthetic and fictional, generated locally. No real companies, no real people, no real emails exist in the data. Names are invented; any resemblance to real entities is coincidental and must be labelled as such. Never present the output as real company data or anonymised real data. Generated email addresses use the reserved `.invalid` domain. Every company and record is marked synthetic, and the CLI repeats this boundary.

## Data model reference

All JSON files are UTF-8, sorted by key, indented, and newline terminated. Identifiers are stable within a generated dataset.

| File | Contents and important references |
| --- | --- |
| `company.json` | Fictional profile, reserved `.invalid` website, and synthetic notice. |
| `employees.json` | Invented staff, roles, reserved-domain email addresses, company ID, and optional manager ID. |
| `accounts.json` | Fictional CRM accounts and employee account owners. |
| `contacts.json` | Invented CRM contacts. Each contact points to an account. |
| `emails.json` | Email threads with three to five messages. Messages identify sender and recipient records, reply parent, optional forward source, and timestamp. |
| `invoices.json` | Invoices link to an account, its contact, and a spreadsheet ID. Integer cent totals and line items avoid floating-point rounding. |
| `spreadsheets/line_items_*.csv` | Openable CSV spreadsheets with invoice and account IDs, item descriptions, quantities, unit prices, and extended amounts in cents. |
| `tickets.json` | Support tickets reference the opening email message, its thread, a CRM account and contact, and an assigned employee. |
| `documents.json` | Fictional internal notes with references to the company, people, CRM, email, invoice, spreadsheet, and ticket records. |
| `reference_graph.json` | Source, field, and target for each generated cross-reference. |
| `manifest.json` | Schema version, seed, profile, deterministic generated date, counts, graph edge count, and workload estimate. |

`synthwork validate <directory>` checks that references resolve, graph endpoints exist, invoice totals and line details match their CSV rows, replies stay inside their thread and follow their parent in time, tickets link to their opening email and thread, and invoice and ticket dates are consistent. Each violation names a file, record ID, and check code.

`synthwork query --type <type> --q <text>` ranks matching generated records. Use `--type all` to search every data type, `--data <directory>` to select the dataset, and `--limit <n>` to cap results. Ranking favors exact phrases and matches in names, titles, subjects, and invoice numbers.

## Scale profile

The `scale` profile is intended to run end to end on CPU without machine learning packages or GPU support. It creates 1 company, 80 employees, 70 accounts, 220 contacts, 400 email threads with 1,200 to 2,000 messages, 250 invoices, 250 CSV spreadsheets with 500 to 1,250 line items, 140 tickets, and 30 internal documents. The target budget is under 30 seconds on a typical current desktop CPU; the pytest scale check allows 60 seconds for slower CI machines. Storage remains compact because output is plain JSON and CSV.

Stats includes the record counts, date range, reference counts by target type, and a deterministic generation-time workload estimate. The estimate is intentionally stable for identical data; measured wall time is printed by `generate`.

## Development

```powershell
python -m pip install pytest
python -m pytest
```

The checked-in `tests/fixtures/clean` directory validates without violations. `tests/fixtures/planted` contains exactly three intentional consistency faults for invoice reconciliation, ticket chronology, and email thread membership. Rebuild both fixtures with `python tests/fixtures/build_fixtures.py` or pass an output directory as its first argument.
