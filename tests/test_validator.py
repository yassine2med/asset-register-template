import json
from pathlib import Path

from assetregister.__main__ import main
from assetregister.validator import coerce_row, load_schema, read_csv, validate_file, validate_rows

EX = Path(__file__).resolve().parent.parent / "examples"


def good_row(**over):
    row = {
        "asset_id": "HVAC-0001", "name": "Rooftop unit", "category": "HVAC",
        "building": "Building A", "location": "Roof", "install_year": 2012,
        "expected_life_years": 20, "condition": "Fair", "replacement_cost": 48000.0,
        "status": "Active",
    }
    row.update(over)
    return row


def test_schema_loads_and_is_valid_json():
    schema = load_schema()
    assert schema["type"] == "object"
    assert "asset_id" in schema["required"]


def test_valid_row_has_no_issues():
    assert validate_rows([good_row()]) == []


def test_valid_example_file_passes():
    count, issues = validate_file(EX / "assets_valid.csv")
    assert count == 6
    assert issues == []


def test_bad_id_pattern():
    issues = validate_rows([good_row(asset_id="hvac-2")])
    assert any(i.field == "asset_id" for i in issues)


def test_unknown_category_and_condition():
    issues = validate_rows([good_row(category="Lighting", condition="Excellent")])
    assert {i.field for i in issues} == {"category", "condition"}


def test_missing_required_value_reports_field_name():
    row = good_row()
    del row["location"]
    issues = validate_rows([row])
    assert [(i.field, i.message) for i in issues] == [("location", "missing required value")]


def test_negative_cost_rejected():
    assert validate_rows([good_row(replacement_cost=-5.0)])


def test_duplicate_ids_reported_at_register_level():
    issues = validate_rows([good_row(), good_row()])
    assert any(i.row == 0 and "2 times" in i.message for i in issues)


def test_coerce_row_types_and_blanks():
    row = coerce_row({"install_year": "2010", "replacement_cost": "12.5", "manufacturer": " ", "name": "x"})
    assert row == {"install_year": 2010, "replacement_cost": 12.5, "name": "x"}


def test_unconvertible_number_becomes_type_error():
    assert coerce_row({"install_year": "twenty"})["install_year"] == "twenty"
    issues = validate_rows([good_row(install_year="twenty")])
    assert any(i.field == "install_year" for i in issues)


def test_extra_column_rejected():
    assert validate_rows([good_row(color="red")])


def test_error_example_file_finds_problems():
    count, issues = validate_file(EX / "assets_with_errors.csv")
    assert count == 6
    assert len(issues) >= 6


def test_cli_exit_codes(tmp_path):
    assert main(["validate", str(EX / "assets_valid.csv")]) == 0
    assert main(["validate", str(EX / "assets_with_errors.csv")]) == 1
    assert main(["validate", str(tmp_path / "nope.csv")]) == 2


def test_cli_schema_prints_json(capsys):
    assert main(["schema"]) == 0
    assert json.loads(capsys.readouterr().out)["title"] == "Facility asset"


def test_read_csv_returns_typed_rows():
    rows = read_csv(EX / "assets_valid.csv")
    assert rows[0]["install_year"] == 2012
