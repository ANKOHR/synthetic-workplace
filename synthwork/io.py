"""Stable JSON and CSV loading helpers."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .constants import COLLECTION_FILES


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def load_dataset(directory: str | Path) -> dict[str, Any]:
    root = Path(directory)
    result: dict[str, Any] = {"root": root}
    for collection, filename in COLLECTION_FILES.items():
        result[collection] = read_json(root / filename)
    result["manifest"] = read_json(root / "manifest.json")
    result["reference_graph"] = read_json(root / "reference_graph.json")
    result["spreadsheets"] = load_spreadsheets(root)
    return result


def load_spreadsheets(root: Path) -> list[dict[str, Any]]:
    folder = root / "spreadsheets"
    sheets: list[dict[str, Any]] = []
    if not folder.exists():
        return sheets
    for path in sorted(folder.glob("*.csv"), key=lambda item: item.name):
        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            rows = list(csv.DictReader(stream))
        if not rows:
            continue
        first = rows[0]
        try:
            normalized_rows = [
                {
                    "line_id": row["line_id"],
                    "description": row["description"],
                    "quantity": int(row["quantity"]),
                    "unit_price_cents": int(row["unit_price_cents"]),
                    "amount_cents": int(row["amount_cents"]),
                }
                for row in rows
            ]
        except (KeyError, TypeError, ValueError):
            normalized_rows = []
        sheets.append(
            {
                "id": first.get("spreadsheet_id", path.stem),
                "title": first.get("title", path.stem),
                "invoice_id": first.get("invoice_id", ""),
                "account_id": first.get("account_id", ""),
                "rows": normalized_rows,
                "file": path.relative_to(root).as_posix(),
            }
        )
    return sheets


def iter_records(dataset: dict[str, Any], collection: str) -> list[dict[str, Any]]:
    if collection == "company":
        value = dataset[collection]
        return [value] if isinstance(value, dict) else []
    value = dataset.get(collection, [])
    return value if isinstance(value, list) else []
