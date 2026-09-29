from __future__ import annotations

from pathlib import Path

from synthwork.query import query_dataset
from synthwork.stats import dataset_stats
from synthwork.io import load_dataset


def test_fixture_queries_find_planted_records_across_data_types(clean_fixture: Path) -> None:
    cases = (
        ("emails", "Quartz Beacon mail marker", "thread_0001"),
        ("accounts", "Quartz Beacon account marker", "account_0001"),
        ("contacts", "Quartz Beacon contact marker", "contact_0001"),
        ("invoices", "Quartz Beacon invoice marker", "invoice_0001"),
        ("spreadsheets", "Quartz Beacon workbook marker", "spreadsheet_0001"),
        ("tickets", "Quartz Beacon ticket marker", "ticket_0001"),
        ("documents", "Quartz Beacon memo marker", "document_0001"),
    )
    for data_type, query, expected_id in cases:
        results = query_dataset(clean_fixture, data_type, query)
        assert results
        assert results[0]["id"] == expected_id
        assert results[0]["score"] > 0


def test_query_ranking_prefers_exact_field_and_limits_results(clean_fixture: Path) -> None:
    results = query_dataset(clean_fixture, "all", "Quartz Beacon ticket marker", limit=20)
    assert results[0]["type"] == "tickets"
    assert results[0]["id"] == "ticket_0001"
    assert all(results[index]["score"] >= results[index + 1]["score"] for index in range(len(results) - 1))
    assert len(query_dataset(clean_fixture, "all", "Quartz Beacon ticket marker", limit=1)) == 1


def test_stats_counts_dates_references_and_estimated_generation_time(clean_fixture: Path) -> None:
    result = dataset_stats(clean_fixture)
    data = load_dataset(clean_fixture)
    manifest = data["manifest"]
    assert result["counts"]["company"] == 1
    assert result["counts"]["employees"] == len(data["employees"])
    assert result["counts"]["emails"] == len(data["emails"])
    assert result["counts"]["email_messages"] == sum(len(thread["messages"]) for thread in data["emails"])
    assert result["counts"]["spreadsheets"] == len(data["spreadsheets"])
    assert result["reference_count"] == manifest["reference_count"]
    assert result["generation_time_ms"] == manifest["generation_time_estimate_ms"]
    assert result["date_range"]["start"] <= result["date_range"]["end"]
    assert sum(result["references_by_target_type"].values()) == result["reference_count"]
