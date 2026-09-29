from __future__ import annotations

import json
from pathlib import Path

from synthwork.validation import validate_dataset
from tests.fixtures.build_fixtures import build_fixtures


def test_checked_in_clean_fixture_has_zero_violations(clean_fixture: Path) -> None:
    result = validate_dataset(clean_fixture)
    assert result["valid"] is True
    assert result["violation_count"] == 0
    assert result["violations"] == []


def test_planted_fixture_reports_exactly_three_known_violations(planted_fixture: Path) -> None:
    result = validate_dataset(planted_fixture)
    assert result["valid"] is False
    assert result["violation_count"] == 3
    assert {
        (item["code"], item["file"], item["record_id"])
        for item in result["violations"]
    } == {
        ("invoice_spreadsheet_mismatch", "invoices.json", "invoice_0001"),
        ("ticket_date_order", "tickets.json", "ticket_0001"),
        ("email_parent_thread_mismatch", "emails.json", "email_0007_05"),
    }
    assert all(item["message"] for item in result["violations"])


def test_fixture_builder_reproduces_checked_in_files(tmp_path: Path) -> None:
    root = tmp_path / "fixtures"
    identifiers = build_fixtures(root)
    assert identifiers == {
        "invoice_id": "invoice_0001",
        "ticket_id": "ticket_0001",
        "email_message_id": "email_0007_05",
    }
    for kind in ("clean", "planted"):
        expected = Path(__file__).parent / "fixtures" / kind
        rebuilt = root / kind
        expected_files = {item.relative_to(expected).as_posix(): item.read_bytes() for item in expected.rglob("*") if item.is_file()}
        rebuilt_files = {item.relative_to(rebuilt).as_posix(): item.read_bytes() for item in rebuilt.rglob("*") if item.is_file()}
        assert rebuilt_files == expected_files


def test_validator_reports_file_and_record_id_for_a_missing_reference(clean_fixture: Path) -> None:
    tickets_file = clean_fixture / "tickets.json"
    tickets = json.loads(tickets_file.read_text(encoding="utf-8"))
    tickets[0]["email_id"] = "email_missing_fixture"
    tickets_file.write_text(json.dumps(tickets), encoding="utf-8")
    result = validate_dataset(clean_fixture)
    found = [item for item in result["violations"] if item["code"] == "unresolved_reference" and item["record_id"] == "ticket_0001"]
    assert len(found) == 1
    assert found[0]["file"] == "tickets.json"
