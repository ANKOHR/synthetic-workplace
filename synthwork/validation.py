"""Referential, amount, thread, and date checks for generated workspaces."""

from __future__ import annotations

from collections import Counter
from datetime import date, datetime
from pathlib import Path
from typing import Any

from .constants import COLLECTION_FILES
from .io import load_dataset


def _parse_date(value: Any) -> datetime | date | None:
    if not isinstance(value, str):
        return None
    try:
        if "T" in value:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        return date.fromisoformat(value)
    except ValueError:
        return None


def validate_dataset(directory: str | Path) -> dict[str, Any]:
    """Return every detected violation with its source file and record id."""
    root = Path(directory)
    try:
        data = load_dataset(root)
    except (OSError, ValueError, TypeError) as error:
        return {
            "valid": False,
            "violation_count": 1,
            "violations": [
                {
                    "code": "dataset_read_error",
                    "file": "dataset",
                    "record_id": "dataset",
                    "message": f"Could not read generated dataset: {error}",
                }
            ],
        }

    violations: list[dict[str, str]] = []

    def report(code: str, filename: str, record_id: str, message: str) -> None:
        violations.append(
            {"code": code, "file": filename, "record_id": str(record_id), "message": message}
        )

    company = data["company"] if isinstance(data["company"], dict) else {}
    ids: dict[str, set[str]] = {"company": set(), "emails": set()}
    ids["company"] = {str(company["id"])} if company.get("id") else set()
    records_by_type: dict[str, list[dict[str, Any]]] = {}
    files_by_type = dict(COLLECTION_FILES)
    files_by_type["spreadsheets"] = "spreadsheets/*.csv"
    for collection in (
        "employees", "accounts", "contacts", "invoices", "tickets", "documents", "spreadsheets"
    ):
        records = data.get(collection, [])
        records_by_type[collection] = records if isinstance(records, list) else []
        ids[collection] = set()
        for record in records_by_type[collection]:
            record_id = str(record.get("id", ""))
            if not record_id:
                report("missing_record_id", files_by_type[collection], "unknown", "Record has no id.")
            elif record_id in ids[collection]:
                report("duplicate_record_id", files_by_type[collection], record_id, "Record id is duplicated.")
            ids[collection].add(record_id)

    message_lookup: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
    thread_lookup: dict[str, dict[str, Any]] = {}
    for thread in data.get("emails", []) if isinstance(data.get("emails"), list) else []:
        thread_id = str(thread.get("id", ""))
        if not thread_id:
            report("missing_record_id", "emails.json", "unknown", "Email thread has no id.")
        elif thread_id in thread_lookup:
            report("duplicate_record_id", "emails.json", thread_id, "Email thread id is duplicated.")
        thread_lookup[thread_id] = thread
        ids["emails"].add(thread_id)
        messages = thread.get("messages", [])
        if not isinstance(messages, list) or len(messages) < 2:
            report("incomplete_email_thread", "emails.json", thread_id or "unknown", "Email thread must contain at least two messages.")
            continue
        previous_time: datetime | None = None
        for message_index, message in enumerate(messages):
            message_id = str(message.get("id", ""))
            if not message_id:
                report("missing_record_id", "emails.json", thread_id or "unknown", "Email message has no id.")
                continue
            if message_id in message_lookup:
                report("duplicate_record_id", "emails.json", message_id, "Email message id is duplicated.")
            message_lookup[message_id] = (thread, message)
            ids["emails"].add(message_id)
            sent_at = _parse_date(message.get("sent_at"))
            if not isinstance(sent_at, datetime):
                report("invalid_email_date", "emails.json", message_id, "Email sent_at is not a valid timestamp.")
            elif previous_time and sent_at < previous_time:
                report("email_date_order", "emails.json", message_id, "Email messages are not in chronological order.")
            if isinstance(sent_at, datetime):
                previous_time = sent_at
            if message_index == 0 and message.get("in_reply_to"):
                report("email_thread_root_has_parent", "emails.json", message_id, "First message in a thread cannot have a reply parent.")
            elif message_index > 0 and not message.get("in_reply_to"):
                report("email_reply_parent_missing", "emails.json", message_id, "Reply message has no parent email.")

    def ref(filename: str, record_id: str, field: str, target_type: str, target_id: Any) -> bool:
        if target_id is None or target_id == "":
            return True
        if str(target_id) not in ids.get(target_type, set()):
            report(
                "unresolved_reference", filename, record_id,
                f"{field} points to missing {target_type} record {target_id}.",
            )
            return False
        return True

    if not company.get("id"):
        report("missing_record_id", "company.json", "unknown", "Company profile has no id.")
    company_id = str(company.get("id", ""))
    contact_lookup = {str(item.get("id", "")): item for item in data.get("contacts", [])}

    for employee in data.get("employees", []):
        record_id = str(employee.get("id", "unknown"))
        employee_company_id = employee.get("company_id")
        ref("employees.json", record_id, "company_id", "company", employee_company_id)
        if employee_company_id and str(employee_company_id) != company_id:
            report("employee_company_mismatch", "employees.json", record_id, "Employee belongs to a different company profile.")
        ref("employees.json", record_id, "manager_id", "employees", employee.get("manager_id"))
    for account in data.get("accounts", []):
        ref("accounts.json", str(account.get("id", "unknown")), "account_owner_id", "employees", account.get("account_owner_id"))
    for contact in data.get("contacts", []):
        ref("contacts.json", str(contact.get("id", "unknown")), "account_id", "accounts", contact.get("account_id"))
    for thread in data.get("emails", []):
        thread_id = str(thread.get("id", "unknown"))
        ref("emails.json", thread_id, "account_id", "accounts", thread.get("account_id"))
        ref("emails.json", thread_id, "contact_id", "contacts", thread.get("contact_id"))
        thread_contact = contact_lookup.get(str(thread.get("contact_id", "")))
        if thread_contact and thread_contact.get("account_id") != thread.get("account_id"):
            report("email_contact_account_mismatch", "emails.json", thread_id, "Email contact belongs to a different account than the thread.")
        for message in thread.get("messages", []) if isinstance(thread.get("messages"), list) else []:
            message_id = str(message.get("id", "unknown"))
            for field, target_type in (
                ("from_employee_id", "employees"), ("from_contact_id", "contacts"),
                ("to_employee_id", "employees"), ("to_contact_id", "contacts"),
                ("in_reply_to", "emails"), ("forwarded_from", "emails"),
            ):
                ref("emails.json", message_id, field, target_type, message.get(field))
            parent_id = message.get("in_reply_to")
            if parent_id in message_lookup:
                parent_thread, parent = message_lookup[str(parent_id)]
                if parent_thread.get("id") != thread.get("id"):
                    report("email_parent_thread_mismatch", "emails.json", message_id, "Reply parent belongs to a different email thread.")
                sent_at = _parse_date(message.get("sent_at"))
                parent_at = _parse_date(parent.get("sent_at"))
                if isinstance(sent_at, datetime) and isinstance(parent_at, datetime) and sent_at < parent_at:
                    report("email_reply_date_order", "emails.json", message_id, "Reply is dated before its parent message.")
            forwarded_id = message.get("forwarded_from")
            if forwarded_id in message_lookup and message_lookup[str(forwarded_id)][0].get("id") != thread.get("id"):
                report("email_forward_thread_mismatch", "emails.json", message_id, "Forward source belongs to a different email thread.")

    sheet_by_id = {str(sheet.get("id", "")): sheet for sheet in data.get("spreadsheets", [])}
    for invoice in data.get("invoices", []):
        record_id = str(invoice.get("id", "unknown"))
        ref("invoices.json", record_id, "account_id", "accounts", invoice.get("account_id"))
        ref("invoices.json", record_id, "contact_id", "contacts", invoice.get("contact_id"))
        invoice_contact = contact_lookup.get(str(invoice.get("contact_id", "")))
        if invoice_contact and invoice_contact.get("account_id") != invoice.get("account_id"):
            report("invoice_contact_account_mismatch", "invoices.json", record_id, "Invoice contact belongs to a different account than the invoice.")
        sheet_id = str(invoice.get("spreadsheet_id", ""))
        sheet_resolves = ref("invoices.json", record_id, "spreadsheet_id", "spreadsheets", sheet_id)
        issued = _parse_date(invoice.get("issued_date"))
        due = _parse_date(invoice.get("due_date"))
        if issued is None or due is None:
            report("invalid_invoice_date", "invoices.json", record_id, "Invoice issue or due date is invalid.")
        elif due < issued:
            report("invoice_date_order", "invoices.json", record_id, "Invoice due_date is earlier than issued_date.")
        if sheet_resolves and sheet_id in sheet_by_id:
            sheet = sheet_by_id[sheet_id]
            ref(sheet.get("file", "spreadsheets/*.csv"), str(sheet.get("id", "unknown")), "invoice_id", "invoices", sheet.get("invoice_id"))
            ref(sheet.get("file", "spreadsheets/*.csv"), str(sheet.get("id", "unknown")), "account_id", "accounts", sheet.get("account_id"))
            invoice_lines = invoice.get("line_items", [])
            sheet_lines = sheet.get("rows", [])
            invoice_total = invoice.get("total_cents")
            row_total = sum(line.get("amount_cents", 0) for line in sheet_lines)
            line_signature = lambda rows: sorted(
                (line.get("line_id"), line.get("description"), line.get("quantity"), line.get("unit_price_cents"), line.get("amount_cents"))
                for line in rows
            )
            if (
                sheet.get("invoice_id") != record_id
                or invoice_total != row_total
                or invoice_total != sum(line.get("amount_cents", 0) for line in invoice_lines)
                or line_signature(invoice_lines) != line_signature(sheet_lines)
            ):
                report("invoice_spreadsheet_mismatch", "invoices.json", record_id, "Invoice totals or line items do not match its spreadsheet rows.")

    for ticket in data.get("tickets", []):
        record_id = str(ticket.get("id", "unknown"))
        ref("tickets.json", record_id, "email_id", "emails", ticket.get("email_id"))
        ref("tickets.json", record_id, "email_thread_id", "emails", ticket.get("email_thread_id"))
        ref("tickets.json", record_id, "account_id", "accounts", ticket.get("account_id"))
        ref("tickets.json", record_id, "contact_id", "contacts", ticket.get("contact_id"))
        ref("tickets.json", record_id, "assigned_employee_id", "employees", ticket.get("assigned_employee_id"))
        ticket_contact = contact_lookup.get(str(ticket.get("contact_id", "")))
        if ticket_contact and ticket_contact.get("account_id") != ticket.get("account_id"):
            report("ticket_contact_account_mismatch", "tickets.json", record_id, "Ticket contact belongs to a different account than the ticket.")
        opening = message_lookup.get(str(ticket.get("email_id", "")))
        if opening:
            if opening[0].get("id") != ticket.get("email_thread_id"):
                report("ticket_email_thread_mismatch", "tickets.json", record_id, "Opening email does not belong to the ticket's linked thread.")
            first_message = opening[0].get("messages", [{}])[0]
            if first_message.get("id") != ticket.get("email_id"):
                report("ticket_email_not_thread_opening", "tickets.json", record_id, "Ticket email is not the first message in its thread.")
            if opening[0].get("account_id") != ticket.get("account_id") or opening[0].get("contact_id") != ticket.get("contact_id"):
                report("ticket_crm_mismatch", "tickets.json", record_id, "Ticket account or contact does not match its email thread.")
            created_at = _parse_date(ticket.get("created_at"))
            sent_at = _parse_date(opening[1].get("sent_at"))
            if not isinstance(created_at, datetime) or not isinstance(sent_at, datetime):
                report("invalid_ticket_date", "tickets.json", record_id, "Ticket or opening email date is invalid.")
            elif created_at < sent_at:
                report("ticket_date_order", "tickets.json", record_id, "Ticket was created before its opening email.")

    for document in data.get("documents", []):
        record_id = str(document.get("id", "unknown"))
        for reference in document.get("references", []):
            target_type = str(reference.get("type", ""))
            ref("documents.json", record_id, "references", target_type, reference.get("id"))

    graph_edges = data.get("reference_graph", []) if isinstance(data.get("reference_graph"), list) else []
    for edge in graph_edges:
        source_type = str(edge.get("source_type", ""))
        source_id = str(edge.get("source_id", ""))
        target_type = str(edge.get("target_type", ""))
        target_id = str(edge.get("target_id", ""))
        if source_id not in ids.get(source_type, set()):
            report("reference_graph_source_missing", "reference_graph.json", source_id or "unknown", f"Graph source is missing from {source_type}.")
        if target_id not in ids.get(target_type, set()):
            report("reference_graph_target_missing", "reference_graph.json", source_id or "unknown", f"Graph target {target_id} is missing from {target_type}.")

    expected_edges: list[tuple[str, str, str, str, str]] = []

    def expect(source_type: str, source_id: Any, field: str, target_type: str, target_id: Any) -> None:
        if target_id:
            expected_edges.append((source_type, str(source_id), field, target_type, str(target_id)))

    for employee in data.get("employees", []):
        expect("employees", employee.get("id"), "company_id", "company", employee.get("company_id"))
        expect("employees", employee.get("id"), "manager_id", "employees", employee.get("manager_id"))
    for thread in data.get("emails", []):
        expect("emails", thread.get("id"), "account_id", "accounts", thread.get("account_id"))
        expect("emails", thread.get("id"), "contact_id", "contacts", thread.get("contact_id"))
        for message in thread.get("messages", []) if isinstance(thread.get("messages"), list) else []:
            expect("emails", message.get("id"), "thread_id", "emails", thread.get("id"))
            for field, target_type in (
                ("from_employee_id", "employees"), ("from_contact_id", "contacts"),
                ("to_employee_id", "employees"), ("to_contact_id", "contacts"),
                ("in_reply_to", "emails"), ("forwarded_from", "emails"),
            ):
                expect("emails", message.get("id"), field, target_type, message.get(field))
    for contact in data.get("contacts", []):
        expect("contacts", contact.get("id"), "account_id", "accounts", contact.get("account_id"))
    for invoice in data.get("invoices", []):
        expect("invoices", invoice.get("id"), "account_id", "accounts", invoice.get("account_id"))
        expect("invoices", invoice.get("id"), "contact_id", "contacts", invoice.get("contact_id"))
        expect("invoices", invoice.get("id"), "spreadsheet_id", "spreadsheets", invoice.get("spreadsheet_id"))
    for sheet in data.get("spreadsheets", []):
        expect("spreadsheets", sheet.get("id"), "invoice_id", "invoices", sheet.get("invoice_id"))
        expect("spreadsheets", sheet.get("id"), "account_id", "accounts", sheet.get("account_id"))
    for ticket in data.get("tickets", []):
        for field, target_type in (
            ("email_id", "emails"), ("email_thread_id", "emails"),
            ("account_id", "accounts"), ("contact_id", "contacts"),
            ("assigned_employee_id", "employees"),
        ):
            expect("tickets", ticket.get("id"), field, target_type, ticket.get(field))
    for document in data.get("documents", []):
        for reference in document.get("references", []):
            expect("documents", document.get("id"), "references", reference.get("type", ""), reference.get("id"))

    def edge_tuple(edge: dict[str, Any]) -> tuple[str, str, str, str, str]:
        return (
            str(edge.get("source_type", "")), str(edge.get("source_id", "")),
            str(edge.get("field", "")), str(edge.get("target_type", "")),
            str(edge.get("target_id", "")),
        )

    expected_counts = Counter(expected_edges)
    actual_counts = Counter(edge_tuple(edge) for edge in graph_edges)
    for edge, count in sorted((expected_counts - actual_counts).items()):
        report("reference_graph_incomplete", "reference_graph.json", edge[1] or "unknown", f"Graph omits {count} reference(s) for {edge[0]}.{edge[2]} to {edge[3]} {edge[4]}.")
    for edge, count in sorted((actual_counts - expected_counts).items()):
        report("reference_graph_inconsistent", "reference_graph.json", edge[1] or "unknown", f"Graph has {count} unexpected reference(s) for {edge[0]}.{edge[2]} to {edge[3]} {edge[4]}.")

    violations.sort(key=lambda item: (item["file"], item["record_id"], item["code"], item["message"]))
    return {
        "valid": not violations,
        "violation_count": len(violations),
        "violations": violations,
        "dataset": str(root),
    }
