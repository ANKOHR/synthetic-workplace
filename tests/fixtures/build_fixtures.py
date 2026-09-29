"""Rebuild checked in deterministic clean and planted test datasets."""

from __future__ import annotations

import csv
import json
import shutil
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from synthwork.generator import generate_dataset

FIXTURE_SEED = 29_092_026
MARKERS = {
    "email": "Quartz Beacon mail marker",
    "account": "Quartz Beacon account marker",
    "contact": "Quartz Beacon contact marker",
    "invoice": "Quartz Beacon invoice marker",
    "spreadsheet": "Quartz Beacon workbook marker",
    "ticket": "Quartz Beacon ticket marker",
    "document": "Quartz Beacon memo marker",
}


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def _patch_csv(path: Path, line_id: str, description: str) -> None:
    with path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        columns = list(reader.fieldnames or [])
        rows = list(reader)
    for row in rows:
        if row["line_id"] == line_id:
            row["description"] = description
            break
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def build_fixtures(base: str | Path) -> dict[str, str]:
    root = Path(base)
    clean = root / "clean"
    planted = root / "planted"
    for target in (clean, planted):
        if target.exists():
            shutil.rmtree(target)
    root.mkdir(parents=True, exist_ok=True)
    clean.mkdir(parents=True)
    generate_dataset(FIXTURE_SEED, clean, "fixture")

    emails = _read(clean / "emails.json")
    email_thread = emails[0]
    email_thread["subject"] = MARKERS["email"]
    email_thread["messages"][0]["subject"] = MARKERS["email"]
    email_thread["messages"][0]["body"] = f"{MARKERS['email']}: fictional fixture correspondence."
    _write(clean / "emails.json", emails)

    accounts = _read(clean / "accounts.json")
    accounts[0]["name"] = f"{MARKERS['account']} cooperative"
    _write(clean / "accounts.json", accounts)

    contacts = _read(clean / "contacts.json")
    contacts[0]["name"] = f"{MARKERS['contact']} liaison"
    _write(clean / "contacts.json", contacts)

    invoices = _read(clean / "invoices.json")
    selected_invoice = invoices[0]
    selected_invoice["description"] = f"{MARKERS['invoice']}: fictional line charges."
    selected_invoice["line_items"][0]["description"] = MARKERS["spreadsheet"]
    _write(clean / "invoices.json", invoices)
    selected_csv = clean / "spreadsheets" / f"line_items_{selected_invoice['id']}.csv"
    _patch_csv(selected_csv, selected_invoice["line_items"][0]["line_id"], MARKERS["spreadsheet"])

    tickets = _read(clean / "tickets.json")
    tickets[0]["subject"] = f"{MARKERS['ticket']}: delivery question"
    _write(clean / "tickets.json", tickets)

    documents = _read(clean / "documents.json")
    documents[0]["title"] = MARKERS["document"]
    _write(clean / "documents.json", documents)

    planted.mkdir(parents=True)
    for source in clean.rglob("*"):
        if source.is_file():
            destination = planted / source.relative_to(clean)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)

    planted_invoices = _read(planted / "invoices.json")
    planted_invoices[0]["total_cents"] += 7
    _write(planted / "invoices.json", planted_invoices)
    planted_tickets = _read(planted / "tickets.json")
    planted_tickets[0]["created_at"] = "2000-01-01T00:00:00Z"
    _write(planted / "tickets.json", planted_tickets)
    planted_emails = _read(planted / "emails.json")
    earliest = min(planted_emails, key=lambda thread: thread["messages"][0]["sent_at"])
    latest = max(planted_emails, key=lambda thread: thread["messages"][0]["sent_at"])
    child = latest["messages"][-1]
    child["in_reply_to"] = earliest["messages"][0]["id"]
    _write(planted / "emails.json", planted_emails)
    graph = _read(planted / "reference_graph.json")
    for edge in graph:
        if edge.get("source_id") == child["id"] and edge.get("field") == "in_reply_to":
            edge["target_id"] = earliest["messages"][0]["id"]
    _write(planted / "reference_graph.json", graph)

    return {
        "invoice_id": planted_invoices[0]["id"],
        "ticket_id": planted_tickets[0]["id"],
        "email_message_id": child["id"],
    }


if __name__ == "__main__":
    destination = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent
    identifiers = build_fixtures(destination)
    print(f"Built clean and planted fixtures in {destination}: {identifiers}")
