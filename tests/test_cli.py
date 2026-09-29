from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from synthwork.constants import HONESTY_HELP, NOTICE

ROOT = Path(__file__).resolve().parents[1]


def _run(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "synthwork", *arguments],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_help_states_honesty_boundary() -> None:
    result = _run("--help")
    assert result.returncode == 0
    assert HONESTY_HELP in result.stdout
    assert "generate" in result.stdout and "validate" in result.stdout


def test_subcommand_help_states_honesty_boundary() -> None:
    for command in ("generate", "validate", "query", "stats"):
        result = _run(command, "--help")
        assert result.returncode == 0
        assert "HONESTY BOUNDARY" in result.stdout
        assert "synthetic and fictional" in result.stdout


def test_cli_generate_validate_query_stats_end_to_end(tmp_path: Path) -> None:
    output = tmp_path / "cli-org"
    generated = _run("generate", "--seed", "808", "--out", str(output), "--profile", "fixture")
    assert generated.returncode == 0, generated.stderr
    assert NOTICE in generated.stdout
    assert "Elapsed generation time:" in generated.stdout

    validated = _run("validate", str(output))
    assert validated.returncode == 0, validated.stdout + validated.stderr
    assert "Validation passed: zero violations." in validated.stdout

    queried = _run("query", "--data", str(output), "--type", "all", "--q", "planning")
    assert queried.returncode == 0, queried.stderr
    assert NOTICE in queried.stdout
    assert '"score"' in queried.stdout
    assert "Found " in queried.stdout

    stats = _run("stats", str(output))
    assert stats.returncode == 0, stats.stderr
    assert NOTICE in stats.stdout
    assert '"generation_time_kind"' in stats.stdout
    assert '"reference_count"' in stats.stdout


def test_each_command_output_states_synthetic_boundary(tmp_path: Path) -> None:
    output = tmp_path / "org"
    assert _run("generate", "--seed", "4", "--out", str(output), "--profile", "fixture").returncode == 0
    for command in (
        _run("validate", str(output)),
        _run("query", "--data", str(output), "--type", "company", "--q", "company"),
        _run("stats", str(output)),
    ):
        assert NOTICE in command.stdout
        assert "fictional" in command.stdout.casefold()


def test_generate_rejects_invalid_seed_with_clear_exit(tmp_path: Path) -> None:
    result = _run("generate", "--seed", "-1", "--out", str(tmp_path / "bad"))
    assert result.returncode == 2
    assert "seed must be an integer" in result.stderr
