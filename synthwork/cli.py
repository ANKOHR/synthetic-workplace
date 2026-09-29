"""Command line interface for SyntheticWorkplace."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from .constants import HONESTY_HELP, NOTICE, PROFILES, QUERY_TYPES
from .generator import generate_dataset
from .query import query_dataset
from .stats import dataset_stats
from .validation import validate_dataset


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="synthwork",
        description="Generate and inspect a fictional workplace for safe agent training.",
        epilog=HONESTY_HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    sub_help = argparse.RawDescriptionHelpFormatter

    generate = subparsers.add_parser(
        "generate", help="create a deterministic fictional organisation",
        description="Create a cross-linked SyntheticWorkplace dataset.", epilog=HONESTY_HELP,
        formatter_class=sub_help,
    )
    generate.add_argument("--seed", required=True, type=int, help="integer seed from 0 through 4294967295")
    generate.add_argument("--out", required=True, type=Path, help="output directory")
    generate.add_argument("--profile", choices=tuple(PROFILES), default="demo", help="volume profile, default: demo")

    validate = subparsers.add_parser(
        "validate", help="check cross-references, totals, threads, and dates",
        description="Check a generated dataset for consistency.", epilog=HONESTY_HELP,
        formatter_class=sub_help,
    )
    validate.add_argument("directory", type=Path, help="generated dataset directory")

    query = subparsers.add_parser(
        "query", help="rank a text search across generated records",
        description="Search generated content with stable relevance ranking.", epilog=HONESTY_HELP,
        formatter_class=sub_help,
    )
    query.add_argument("--type", required=True, choices=QUERY_TYPES, help="data type to search, or all")
    query.add_argument("--q", required=True, help="search text")
    query.add_argument("--data", type=Path, default=Path("."), help="dataset directory, default: current directory")
    query.add_argument("--limit", type=int, default=20, help="maximum results, default: 20")

    stats = subparsers.add_parser(
        "stats", help="summarize volume, dates, references, and generation estimate",
        description="Report a dataset volume profile and deterministic generation-time estimate.",
        epilog=HONESTY_HELP,
        formatter_class=sub_help,
    )
    stats.add_argument("directory", type=Path, help="generated dataset directory")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    print(NOTICE)
    try:
        if args.command == "generate":
            result = generate_dataset(args.seed, args.out, args.profile)
            counts = result["manifest"]["counts"]
            print(
                f"Generated fictional {args.profile} organisation in {args.out}. "
                f"Records: {sum(value for key, value in counts.items() if key != 'email_messages')}; "
                f"email messages: {counts['email_messages']}."
            )
            print(f"Elapsed generation time: {result['elapsed_ms']:.2f} ms.")
            print(f"Run 'synthwork validate {args.out}' to check consistency.")
            return 0
        if args.command == "validate":
            result = validate_dataset(args.directory)
            if result["valid"]:
                print("Validation passed: zero violations.")
                return 0
            print(f"Validation failed: {result['violation_count']} violation(s).")
            for violation in result["violations"]:
                print(
                    f"{violation['file']} record {violation['record_id']} "
                    f"[{violation['code']}]: {violation['message']}"
                )
            return 1
        if args.command == "query":
            results = query_dataset(args.data, args.type, args.q, args.limit)
            print(json.dumps(results, ensure_ascii=False, indent=2, sort_keys=True))
            print(f"Found {len(results)} ranked result(s).")
            return 0
        if args.command == "stats":
            print(json.dumps(dataset_stats(args.directory), ensure_ascii=False, indent=2, sort_keys=True))
            return 0
    except (OSError, ValueError, TypeError, KeyError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2
    parser.error("unknown command")
    return 2
