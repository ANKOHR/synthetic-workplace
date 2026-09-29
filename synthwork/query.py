"""Ranked full text search over every generated data type."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .constants import COLLECTION_ORDER
from .io import load_dataset

_WORD = re.compile(r"[a-z0-9]+")
_FIELD_BOOST = {"name": 18, "title": 18, "subject": 18, "number": 18, "summary": 14, "description": 10, "body": 8}


def _strings(value: Any, prefix: str = "") -> list[tuple[str, str]]:
    output: list[tuple[str, str]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            output.extend(_strings(child, path))
    elif isinstance(value, list):
        for child in value:
            output.extend(_strings(child, prefix))
    elif isinstance(value, str):
        output.append((prefix.rsplit(".", 1)[-1].lower(), value.casefold()))
    return output


def _rank(record: dict[str, Any], query: str) -> tuple[int, list[str]]:
    terms = _WORD.findall(query.casefold())
    phrase = " ".join(terms)
    fields = _strings(record)
    if not terms:
        return 0, []
    score = 0
    matches: list[str] = []
    for field, value in fields:
        value_terms = " ".join(_WORD.findall(value))
        if not value_terms:
            continue
        boost = _FIELD_BOOST.get(field, 0)
        if value_terms == phrase:
            score = max(score, 160 + boost)
            matches.append(field)
        elif phrase in value_terms:
            score = max(score, 110 + boost)
            matches.append(field)
        else:
            hits = sum(1 for term in set(terms) if term in value_terms)
            if hits:
                score = max(score, (65 if hits == len(set(terms)) else 20 * hits) + boost)
                matches.append(field)
    return score, sorted(set(matches))


def query_dataset(
    directory: str | Path,
    entity_type: str,
    query: str,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Search a dataset and return stable relevance-ordered records."""
    data = load_dataset(directory)
    if entity_type != "all" and entity_type not in COLLECTION_ORDER:
        raise ValueError(f"unknown data type: {entity_type}")
    if not query.strip():
        raise ValueError("query text must not be empty")
    if limit < 1:
        raise ValueError("limit must be at least 1")

    result: list[dict[str, Any]] = []
    selected = [name for name in COLLECTION_ORDER if entity_type == "all" or name == entity_type]
    for collection in selected:
        records = data[collection]
        if collection == "company":
            records = [records]
        for record in records:
            score, matched_fields = _rank(record, query)
            if score > 0:
                result.append(
                    {
                        "type": collection,
                        "id": str(record.get("id", "unknown")),
                        "score": score,
                        "matched_fields": matched_fields,
                        "record": record,
                    }
                )
    type_order = {name: index for index, name in enumerate(COLLECTION_ORDER)}
    result.sort(key=lambda item: (-item["score"], type_order[item["type"]], item["id"]))
    return result[:limit]
