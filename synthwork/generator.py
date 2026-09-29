"""Seeded workplace entity generation with references built from source records."""

from __future__ import annotations

import csv
import random
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .constants import (
    COMPANY_NOUNS,
    COMPANY_WORDS,
    DEPARTMENTS,
    FIRST_NAMES,
    INDUSTRIES,
    LAST_NAMES,
    PRODUCTS,
    PROFILES,
    PROJECTS,
    ROLES,
)
from .io import write_json


def _person_name(rng: random.Random) -> str:
    return f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"


def _iso(day: date, hour: int = 9, minute: int = 0) -> str:
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def _amount_line(rng: random.Random, index: int) -> dict[str, Any]:
    quantity = rng.randint(1, 8)
    unit_price_cents = rng.randint(350, 24500)
    return {
        "line_id": f"line_{index:03d}",
        "description": rng.choice(PRODUCTS),
        "quantity": quantity,
        "unit_price_cents": unit_price_cents,
        "amount_cents": quantity * unit_price_cents,
    }


def _write_sheet(path: Path, invoice: dict[str, Any], account_name: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = (
        "spreadsheet_id", "title", "invoice_id", "account_id", "account_name",
        "line_id", "description", "quantity", "unit_price_cents", "amount_cents",
    )
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for line in invoice["line_items"]:
            writer.writerow(
                {
                    "spreadsheet_id": invoice["spreadsheet_id"],
                    "title": f"{invoice['number']} line items",
                    "invoice_id": invoice["id"],
                    "account_id": invoice["account_id"],
                    "account_name": account_name,
                    **line,
                }
            )


def _reference_edges(data: dict[str, Any]) -> list[dict[str, str]]:
    edges: list[dict[str, str]] = []

    def add(source_type: str, source_id: str, field: str, target_type: str, target_id: str | None) -> None:
        if target_id:
            edges.append(
                {
                    "source_type": source_type,
                    "source_id": source_id,
                    "field": field,
                    "target_type": target_type,
                    "target_id": target_id,
                }
            )

    company_id = data["company"]["id"]
    for employee in data["employees"]:
        add("employees", employee["id"], "company_id", "company", employee["company_id"])
        add("employees", employee["id"], "manager_id", "employees", employee.get("manager_id"))
    for thread in data["emails"]:
        add("emails", thread["id"], "account_id", "accounts", thread["account_id"])
        add("emails", thread["id"], "contact_id", "contacts", thread["contact_id"])
        for message in thread["messages"]:
            add("emails", message["id"], "thread_id", "emails", thread["id"])
            add("emails", message["id"], "from_employee_id", "employees", message.get("from_employee_id"))
            add("emails", message["id"], "from_contact_id", "contacts", message.get("from_contact_id"))
            add("emails", message["id"], "to_employee_id", "employees", message.get("to_employee_id"))
            add("emails", message["id"], "to_contact_id", "contacts", message.get("to_contact_id"))
            add("emails", message["id"], "in_reply_to", "emails", message.get("in_reply_to"))
            add("emails", message["id"], "forwarded_from", "emails", message.get("forwarded_from"))
    for contact in data["contacts"]:
        add("contacts", contact["id"], "account_id", "accounts", contact["account_id"])
    for invoice in data["invoices"]:
        add("invoices", invoice["id"], "account_id", "accounts", invoice["account_id"])
        add("invoices", invoice["id"], "contact_id", "contacts", invoice["contact_id"])
        add("invoices", invoice["id"], "spreadsheet_id", "spreadsheets", invoice["spreadsheet_id"])
    for sheet in data["spreadsheets"]:
        add("spreadsheets", sheet["id"], "invoice_id", "invoices", sheet["invoice_id"])
        add("spreadsheets", sheet["id"], "account_id", "accounts", sheet["account_id"])
    for ticket in data["tickets"]:
        add("tickets", ticket["id"], "email_id", "emails", ticket["email_id"])
        add("tickets", ticket["id"], "email_thread_id", "emails", ticket["email_thread_id"])
        add("tickets", ticket["id"], "account_id", "accounts", ticket["account_id"])
        add("tickets", ticket["id"], "contact_id", "contacts", ticket["contact_id"])
        add("tickets", ticket["id"], "assigned_employee_id", "employees", ticket["assigned_employee_id"])
    for document in data["documents"]:
        for reference in document["references"]:
            add("documents", document["id"], "references", reference["type"], reference["id"])
    return sorted(edges, key=lambda edge: (edge["source_type"], edge["source_id"], edge["field"], edge["target_type"], edge["target_id"]))


def generate_dataset(seed: int, out: str | Path, profile: str = "demo") -> dict[str, Any]:
    """Generate a deterministic dataset and return runtime and count metadata."""
    started = time.perf_counter()
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0 or seed > 4_294_967_295:
        raise ValueError("seed must be an integer from 0 through 4294967295")
    if profile not in PROFILES:
        raise ValueError(f"profile must be one of: {', '.join(PROFILES)}")

    rng = random.Random(seed)
    root = Path(out)
    root.mkdir(parents=True, exist_ok=True)
    counts = PROFILES[profile]
    origin = date(2024, 1, 1) + timedelta(days=seed % 800)
    company_name = f"{rng.choice(COMPANY_WORDS)} {rng.choice(COMPANY_NOUNS)} {rng.choice(('Works', 'Collective', 'Supply', 'Services'))}"
    company_id = "company_001"
    company = {
        "id": company_id,
        "name": company_name,
        "industry": rng.choice(INDUSTRIES),
        "headquarters": f"{rng.randint(10, 980)} {rng.choice(COMPANY_NOUNS)} Lane, {rng.choice(COMPANY_WORDS)} Bay",
        "website": "https://syntheticworkplace.invalid",
        "fictional_notice": (
            "Synthetic and fictional company profile. No real company or people are represented. "
            "Names are invented; any resemblance to real entities is coincidental."
        ),
        "is_synthetic": True,
    }

    employees: list[dict[str, Any]] = []
    for index in range(1, counts["employees"] + 1):
        name = _person_name(rng)
        employees.append(
            {
                "id": f"employee_{index:04d}",
                "company_id": company_id,
                "name": name,
                "email": f"employee{index:04d}@syntheticworkplace.invalid",
                "role": f"{rng.choice(DEPARTMENTS)} {rng.choice(ROLES)}",
                "department": rng.choice(DEPARTMENTS),
                "manager_id": None if index == 1 else f"employee_{rng.randint(1, index - 1):04d}",
                "start_date": (origin - timedelta(days=rng.randint(15, 2200))).isoformat(),
                "is_synthetic": True,
            }
        )

    accounts: list[dict[str, Any]] = []
    for index in range(1, counts["accounts"] + 1):
        account_name = f"{rng.choice(COMPANY_WORDS)} {rng.choice(COMPANY_NOUNS)} {rng.choice(('Studio', 'Trading', 'Workshop', 'Partners'))}"
        accounts.append(
            {
                "id": f"account_{index:04d}",
                "name": account_name,
                "industry": rng.choice(INDUSTRIES),
                "status": rng.choice(("active", "active", "prospect")),
                "region": rng.choice(("North", "South", "East", "West", "Central")),
                "account_owner_id": rng.choice(employees)["id"],
                "created_date": (origin - timedelta(days=rng.randint(2, 1000))).isoformat(),
                "notes": f"Fictional customer for {rng.choice(PROJECTS).lower()} planning.",
                "is_synthetic": True,
            }
        )

    contacts: list[dict[str, Any]] = []
    for index in range(1, counts["contacts"] + 1):
        name = _person_name(rng)
        contacts.append(
            {
                "id": f"contact_{index:04d}",
                "account_id": accounts[(index - 1) % len(accounts)]["id"] if index <= len(accounts) else rng.choice(accounts)["id"],
                "name": name,
                "email": f"contact{index:04d}@mail.syntheticworkplace.invalid",
                "title": rng.choice(("Buyer", "Planner", "Coordinator", "Operations Lead", "Office Manager")),
                "phone": f"+1-555-01{index % 100:02d}",
                "is_synthetic": True,
            }
        )

    emails: list[dict[str, Any]] = []
    for thread_index in range(1, counts["email_threads"] + 1):
        account = rng.choice(accounts)
        contact = rng.choice([item for item in contacts if item["account_id"] == account["id"]])
        owner = next(employee for employee in employees if employee["id"] == account["account_owner_id"])
        subject = f"{rng.choice(PROJECTS)}: {rng.choice(('availability', 'schedule', 'order details', 'follow up'))}"
        start_day = origin + timedelta(days=rng.randint(0, 420))
        message_count = rng.randint(3, 5)
        messages: list[dict[str, Any]] = []
        for message_index in range(1, message_count + 1):
            message_id = f"email_{thread_index:04d}_{message_index:02d}"
            day = start_day + timedelta(days=message_index - 1)
            inbound = message_index % 2 == 1
            body_detail = rng.choice(PROJECTS).lower()
            if inbound:
                body = f"Could you share an update about {body_detail}? We are planning the next delivery window."
                from_contact_id = contact["id"]
                to_employee_id = owner["id"]
                from_employee_id = None
                to_contact_id = None
            else:
                body = f"We reviewed {body_detail} and have a proposed schedule for your team."
                from_contact_id = None
                to_employee_id = None
                from_employee_id = owner["id"]
                to_contact_id = contact["id"]
            message: dict[str, Any] = {
                "id": message_id,
                "sequence": message_index,
                "sent_at": _iso(day, 8 + (message_index % 8), rng.choice((0, 15, 30, 45))),
                "subject": subject,
                "body": body,
                "from_employee_id": from_employee_id,
                "from_contact_id": from_contact_id,
                "to_employee_id": to_employee_id,
                "to_contact_id": to_contact_id,
                "in_reply_to": None if message_index == 1 else f"email_{thread_index:04d}_{message_index - 1:02d}",
                "forwarded_from": f"email_{thread_index:04d}_{message_index - 1:02d}" if message_index == 3 else None,
                "is_synthetic": True,
            }
            messages.append(message)
        emails.append(
            {
                "id": f"thread_{thread_index:04d}",
                "subject": subject,
                "account_id": account["id"],
                "contact_id": contact["id"],
                "messages": messages,
                "is_synthetic": True,
            }
        )

    invoices: list[dict[str, Any]] = []
    for index in range(1, counts["invoices"] + 1):
        account = rng.choice(accounts)
        contact = rng.choice([item for item in contacts if item["account_id"] == account["id"]])
        line_items = [_amount_line(rng, row) for row in range(1, rng.randint(2, 5) + 1)]
        issue_day = origin + timedelta(days=rng.randint(0, 500))
        invoice_id = f"invoice_{index:04d}"
        invoice = {
            "id": invoice_id,
            "number": f"SW-{origin.year}-{index:05d}",
            "account_id": account["id"],
            "contact_id": contact["id"],
            "spreadsheet_id": f"spreadsheet_{index:04d}",
            "issued_date": issue_day.isoformat(),
            "due_date": (issue_day + timedelta(days=30)).isoformat(),
            "currency": "USD",
            "line_items": line_items,
            "total_cents": sum(line["amount_cents"] for line in line_items),
            "status": rng.choice(("paid", "open", "open", "draft")),
            "description": f"{rng.choice(PROJECTS)} service and supply charges.",
            "is_synthetic": True,
        }
        invoices.append(invoice)

    spreadsheets: list[dict[str, Any]] = []
    account_lookup = {account["id"]: account for account in accounts}
    for invoice in invoices:
        sheet = {
            "id": invoice["spreadsheet_id"],
            "title": f"{invoice['number']} line items",
            "invoice_id": invoice["id"],
            "account_id": invoice["account_id"],
            "rows": [dict(line) for line in invoice["line_items"]],
        }
        spreadsheets.append(sheet)
        _write_sheet(root / "spreadsheets" / f"line_items_{invoice['id']}.csv", invoice, account_lookup[invoice["account_id"]]["name"])
    live_sheet_names = {f"line_items_{invoice['id']}.csv" for invoice in invoices}
    sheet_folder = root / "spreadsheets"
    for stale_file in sheet_folder.glob("line_items_*.csv"):
        if stale_file.name not in live_sheet_names:
            stale_file.unlink()

    tickets: list[dict[str, Any]] = []
    for index in range(1, counts["tickets"] + 1):
        thread = emails[(index * 3 - 1) % len(emails)]
        account = account_lookup[thread["account_id"]]
        opening_message = thread["messages"][0]
        contact = next(item for item in contacts if item["id"] == thread["contact_id"])
        opened_day = date.fromisoformat(opening_message["sent_at"][:10]) + timedelta(days=rng.randint(0, 1))
        tickets.append(
            {
                "id": f"ticket_{index:04d}",
                "subject": f"{rng.choice(('Delivery question', 'Order update', 'Schedule clarification', 'Product follow up'))}: {thread['subject']}",
                "status": rng.choice(("open", "pending", "resolved")),
                "priority": rng.choice(("low", "normal", "normal", "high")),
                "account_id": account["id"],
                "contact_id": contact["id"],
                "email_id": opening_message["id"],
                "email_thread_id": thread["id"],
                "assigned_employee_id": account["account_owner_id"],
                "created_at": _iso(opened_day, 10, 0),
                "description": "Ticket opened from the first customer email in the linked thread.",
                "is_synthetic": True,
            }
        )

    references: list[dict[str, str]] = []
    for name, records in (
        ("employees", employees), ("emails", emails), ("accounts", accounts),
        ("contacts", contacts), ("invoices", invoices), ("spreadsheets", spreadsheets),
        ("tickets", tickets),
    ):
        for record in records:
            references.append({"type": name, "id": record["id"]})
    references.append({"type": "company", "id": company_id})
    documents: list[dict[str, Any]] = []
    for index in range(1, counts["documents"] + 1):
        doc_references = list(references) if index == 1 else rng.sample(references, min(len(references), 12 + index))
        documents.append(
            {
                "id": f"document_{index:04d}",
                "title": f"{rng.choice(PROJECTS)} internal operating note",
                "category": rng.choice(("meeting notes", "process guide", "account brief", "weekly update")),
                "created_at": _iso(origin + timedelta(days=rng.randint(0, 500)), 12, 0),
                "body": f"Internal fictional planning note for {company_name}. Confirm the linked records before acting on {rng.choice(PROJECTS).lower()}.",
                "references": doc_references,
                "is_synthetic": True,
            }
        )

    data: dict[str, Any] = {
        "company": company,
        "employees": employees,
        "emails": emails,
        "accounts": accounts,
        "contacts": contacts,
        "invoices": invoices,
        "spreadsheets": spreadsheets,
        "tickets": tickets,
        "documents": documents,
    }
    graph = _reference_edges(data)
    message_count = sum(len(thread["messages"]) for thread in emails)
    record_count = sum(len(data[name]) if isinstance(data[name], list) else 1 for name in data)
    estimated_ms = max(1, int((record_count + message_count) * 0.12 + 0.5))
    manifest = {
        "schema_version": 1,
        "seed": seed,
        "profile": profile,
        "generated_at": _iso(origin, 0, 0),
        "synthetic": True,
        "counts": {
            "company": 1,
            "employees": len(employees),
            "email_threads": len(emails),
            "email_messages": message_count,
            "accounts": len(accounts),
            "contacts": len(contacts),
            "invoices": len(invoices),
            "spreadsheets": len(spreadsheets),
            "tickets": len(tickets),
            "documents": len(documents),
        },
        "reference_count": len(graph),
        "generation_time_estimate_ms": estimated_ms,
    }
    write_json(root / "company.json", company)
    write_json(root / "employees.json", employees)
    write_json(root / "emails.json", emails)
    write_json(root / "accounts.json", accounts)
    write_json(root / "contacts.json", contacts)
    write_json(root / "invoices.json", invoices)
    write_json(root / "tickets.json", tickets)
    write_json(root / "documents.json", documents)
    write_json(root / "reference_graph.json", graph)
    write_json(root / "manifest.json", manifest)
    elapsed_ms = (time.perf_counter() - started) * 1000
    return {"manifest": manifest, "elapsed_ms": elapsed_ms, "directory": str(root)}
