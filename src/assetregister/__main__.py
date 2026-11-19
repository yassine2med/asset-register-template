"""Command line entry: python -m assetregister validate FILE.csv, or schema."""

from __future__ import annotations

import argparse
import json
import sys

from .validator import load_schema, validate_file


def main(argv: list[str] | None = None) -> int:
    """Run the CLI. Returns 0 when valid, 1 when issues exist, 2 on a missing file."""
    parser = argparse.ArgumentParser(prog="assetregister", description="Asset register validator")
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("validate", help="validate a register CSV")
    check.add_argument("file")
    sub.add_parser("schema", help="print the JSON Schema")
    args = parser.parse_args(argv)

    if args.command == "schema":
        print(json.dumps(load_schema(), indent=2))
        return 0
    try:
        count, issues = validate_file(args.file)
    except FileNotFoundError:
        print(f"File not found: {args.file}", file=sys.stderr)
        return 2
    for issue in issues:
        print(issue)
    print(f"{count} rows checked, {len(issues)} issue(s)")
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
