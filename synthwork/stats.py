"""Dataset volume, date, reference, and deterministic runtime estimate."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from .constants import COLLECTION_ORDER
from .io import load_dataset


def _dates(value: Any) -> list[date]:
    dates: list[date] = []
    if isinstance(value, dict):
        for item in value.values():
            dates.extend(_dates(item))
    elif isinstance(value, list):
        for item in value:
            dates.extend(_dates(item))
    elif isinstance(value, str) and len(value) >= 10:
        try:
            dates.append(date.fromisoformat(value[:10]))
        except ValueError:
            pass
    return dates


def dataset_stats(directory: str | Path) -> dict[str, Any]:
    data = load_dataset(directory)
    counts: dict[str, int] = {}
    for collection in COLLECTION_ORDER:
        value = data[collection]
        counts[collection] = 1 if collection == "company" and isinstance(value, dict) else len(value)
    counts["email_messages"] = sum(len(thread.get("messages", [])) for thread in data["emails"])
    references: dict[str, int] = {}
    for edge in data["reference_graph"]:
        target_type = str(edge.get("target_type", "unknown"))
        references[target_type] = references.get(target_type, 0) + 1
    dates = _dates(
        [data[name] for name in COLLECTION_ORDER]
    )
    return {
        "dataset": str(Path(directory)),
        "seed": data["manifest"].get("seed"),
        "profile": data["manifest"].get("profile"),
        "counts": counts,
        "date_range": {
            "start": min(dates).isoformat() if dates else None,
            "end": max(dates).isoformat() if dates else None,
        },
        "reference_count": len(data["reference_graph"]),
        "references_by_target_type": dict(sorted(references.items())),
        "generation_time_ms": data["manifest"].get("generation_time_estimate_ms"),
        "generation_time_kind": "deterministic workload estimate, not a wall clock measurement",
    }
