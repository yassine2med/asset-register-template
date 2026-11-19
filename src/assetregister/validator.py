"""Validate asset register rows against the JSON Schema plus register-level rules."""

from __future__ import annotations

import csv
import json
from collections import Counter
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

from jsonschema import Draft202012Validator

INTEGER_FIELDS = ("install_year", "expected_life_years")
NUMBER_FIELDS = ("replacement_cost",)


@dataclass(frozen=True)
class Issue:
    """One problem found in the register. Row 0 means a register-level problem."""

    row: int
    field: str
    message: str

    def __str__(self) -> str:
        where = f"row {self.row}" if self.row else "register"
        return f"{where}: {self.field}: {self.message}"


def load_schema() -> dict:
    """Return the bundled asset JSON Schema."""
    text = resources.files("assetregister").joinpath("asset.schema.json").read_text(encoding="utf-8")
    return json.loads(text)


def coerce_row(raw: dict[str, str]) -> dict:
    """Convert CSV strings to the types the schema expects.

    Empty cells are dropped. Values that cannot be converted are left as
    strings so the schema reports them as type errors.
    """
    row: dict = {}
    for key, value in raw.items():
        if key is None:
            continue
        value = (value or "").strip()
        if value == "":
            continue
        try:
            if key in INTEGER_FIELDS:
                row[key] = int(value)
            elif key in NUMBER_FIELDS:
                row[key] = float(value)
            else:
                row[key] = value
        except ValueError:
            row[key] = value
    return row


def read_csv(path: str | Path) -> list[dict]:
    """Read a register CSV and return coerced rows."""
    with open(path, newline="", encoding="utf-8") as handle:
        return [coerce_row(r) for r in csv.DictReader(handle)]


def validate_rows(rows: list[dict]) -> list[Issue]:
    """Validate rows. Row numbers count the first data row as 1."""
    validator = Draft202012Validator(load_schema())
    issues: list[Issue] = []
    for number, row in enumerate(rows, start=1):
        for error in sorted(validator.iter_errors(row), key=lambda e: [str(p) for p in e.path]):
            if error.validator == "required":
                issues.append(Issue(number, error.message.split("'")[1], "missing required value"))
            else:
                field = str(error.path[-1]) if error.path else "(row)"
                issues.append(Issue(number, field, error.message))
    counts = Counter(r.get("asset_id") for r in rows if r.get("asset_id"))
    for asset_id, count in counts.items():
        if count > 1:
            issues.append(Issue(0, "asset_id", f"{asset_id} appears {count} times"))
    return issues


def validate_file(path: str | Path) -> tuple[int, list[Issue]]:
    """Validate a CSV file. Returns (row count, issues)."""
    rows = read_csv(path)
    return len(rows), validate_rows(rows)
