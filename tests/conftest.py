from __future__ import annotations

import shutil
from pathlib import Path

import pytest

FIXTURE_ROOT = Path(__file__).parent / "fixtures"


@pytest.fixture
def clean_fixture(tmp_path: Path) -> Path:
    target = tmp_path / "clean"
    shutil.copytree(FIXTURE_ROOT / "clean", target)
    return target


@pytest.fixture
def planted_fixture(tmp_path: Path) -> Path:
    target = tmp_path / "planted"
    shutil.copytree(FIXTURE_ROOT / "planted", target)
    return target
