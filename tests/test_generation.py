from __future__ import annotations

import hashlib
import time
from pathlib import Path

import pytest

from synthwork.generator import generate_dataset
from synthwork.io import load_dataset
from synthwork.validation import validate_dataset


def _tree_hashes(path: Path) -> dict[str, str]:
    return {
        item.relative_to(path).as_posix(): hashlib.sha256(item.read_bytes()).hexdigest()
        for item in sorted(path.rglob("*"))
        if item.is_file()
    }


def test_same_seed_and_profile_are_byte_identical(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    generate_dataset(123456, first, "fixture")
    generate_dataset(123456, second, "fixture")
    assert _tree_hashes(first) == _tree_hashes(second)


def test_different_seed_changes_generated_org(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    generate_dataset(17, first, "fixture")
    generate_dataset(18, second, "fixture")
    assert _tree_hashes(first) != _tree_hashes(second)
    assert load_dataset(first)["company"]["name"] != load_dataset(second)["company"]["name"] or (
        load_dataset(first)["manifest"]["seed"] != load_dataset(second)["manifest"]["seed"]
    )


def test_generated_cross_references_resolve(tmp_path: Path) -> None:
    target = tmp_path / "org"
    generate_dataset(42, target, "demo")
    result = validate_dataset(target)
    assert result["valid"] is True
    assert result["violations"] == []


def test_seed_validation_is_explicit(tmp_path: Path) -> None:
    for seed in (-1, 4_294_967_296, True):
        with pytest.raises(ValueError, match="seed must be an integer"):
            generate_dataset(seed, tmp_path / "invalid")


def test_scale_profile_finishes_within_cpu_time_budget(tmp_path: Path) -> None:
    target = tmp_path / "scale"
    started = time.perf_counter()
    result = generate_dataset(20260929, target, "scale")
    elapsed_seconds = time.perf_counter() - started
    assert target.exists()
    assert result["manifest"]["counts"]["email_threads"] == 400
    assert result["manifest"]["counts"]["invoices"] == 250
    assert elapsed_seconds < 60


def test_repeated_generation_removes_only_stale_generated_sheets(tmp_path: Path) -> None:
    target = tmp_path / "org"
    generate_dataset(1, target, "scale")
    unrelated = target / "spreadsheets" / "notes.csv"
    unrelated.write_text("kept\n", encoding="utf-8")
    generate_dataset(1, target, "fixture")
    assert unrelated.read_text(encoding="utf-8") == "kept\n"
    assert len(list((target / "spreadsheets").glob("line_items_*.csv"))) == 6
