import json
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "canonical_event_lite" / "src"
sys.path.insert(0, str(SRC))

from canonical_event_lite import build_canonical_lite, read_xml_rows, read_xlsx_rows

def write_xlsx(path: Path):
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr(
            "xl/sharedStrings.xml",
            "<sst><si><t>Player</t></si><si><t>Metric</t></si><si><t>Value</t></si><si><t>Alice</t></si><si><t>Passes</t></si></sst>",
        )
        zf.writestr(
            "xl/worksheets/sheet1.xml",
            "<worksheet><sheetData>"
            "<row r='1'><c r='A1' t='s'><v>0</v></c><c r='B1' t='s'><v>1</v></c><c r='C1' t='s'><v>2</v></c></row>"
            "<row r='2'><c r='A2' t='s'><v>3</v></c><c r='C2'><v>12</v></c></row>"
            "</sheetData></worksheet>",
        )
        zf.writestr(
            "xl/worksheets/sheet2.xml",
            "<worksheet><sheetData>"
            "<row r='1'><c r='A1' t='s'><v>0</v></c><c r='B1' t='s'><v>1</v></c></row>"
            "<row r='2'><c r='A2' t='s'><v>3</v></c><c r='B2' t='s'><v>4</v></c></row>"
            "</sheetData></worksheet>",
        )

def make_match(tmp_path: Path) -> Path:
    match = tmp_path / "runtime" / "active_single_match" / "current"
    raw = match / "raw"
    raw.mkdir(parents=True)
    csv_text = "ID;start;end;code;team;action;half;pos_x;pos_y;unused\n1;5.2;6.0;X;Alpha;Pass;1;20;30;keepme\n"
    (match / "Players.csv").write_text(csv_text, encoding="utf-8")
    (raw / "Players.csv").write_text(csv_text, encoding="utf-8")
    xml = """<file><ALL_INSTANCES>
    <instance><ID>1</ID><start>5.2</start><end>6.0</end><code>X</code>
      <label><group>Half</group><text>1</text></label>
      <label><group>Action</group><text>Pass</text></label>
    </instance>
    </ALL_INSTANCES><SORT_INFO><row><name>not_event</name></row></SORT_INFO></file>"""
    (match / "Players.xml").write_text(xml, encoding="utf-8")
    write_xlsx(match / "Players.xlsx")
    return match

def test_all_source_columns_are_preserved(tmp_path):
    match = make_match(tmp_path)
    rows, audit = build_canonical_lite(match)
    csv_row = next(row for row in rows if row["source_format"] == "csv")
    extras = json.loads(csv_row["source_extra_fields"])
    assert csv_row["source_event_id_raw"] == "1"
    assert csv_row["start_raw"] == "5.2"
    assert csv_row["end_raw"] == "6.0"
    assert csv_row["period_candidate"] == "FIRST_HALF"
    assert extras["unused"] == "keepme"
    assert audit["canonical_event_count"] == "UNKNOWN"

def test_xml_prefers_instance_and_preserves_repeated_labels(tmp_path):
    match = make_match(tmp_path)
    rows, headers = read_xml_rows(match / "Players.xml")
    assert len(rows) == 1
    assert rows[0]["ID"] == "1"
    assert len(rows[0]["__labels__"]) == 2
    assert all(row.get("__xml_node__") == "instance" for row in rows)

def test_xlsx_blank_cells_do_not_shift_columns_and_all_sheets_are_read(tmp_path):
    p = tmp_path / "Players.xlsx"
    write_xlsx(p)
    rows, headers = read_xlsx_rows(p)
    first = rows[0]
    assert first["Player"] == "Alice"
    assert first["Metric"] == ""
    assert first["Value"] == "12"
    assert {row["__source_sheet__"] for row in rows} == {
        "xl/worksheets/sheet1.xml",
        "xl/worksheets/sheet2.xml",
    }

def test_duplicate_root_raw_surface_is_not_double_processed(tmp_path):
    match = make_match(tmp_path)
    rows, audit = build_canonical_lite(match)
    csv_rows = [row for row in rows if row["source_format"] == "csv"]
    assert len(csv_rows) == 1
    assert audit["skipped_duplicate_surfaces"]
    assert audit["status"] == "REVIEW_REQUIRED"

def test_direction_is_blocked_until_evidence_exists(tmp_path):
    match = make_match(tmp_path)
    rows, _ = build_canonical_lite(match)
    row = next(row for row in rows if row["source_format"] == "csv")
    assert row["coordinate_system_candidate"] == "PITCH_105_X_68_CANDIDATE"
    assert row["attacking_direction_candidate"] == "UNKNOWN"
    assert row["directional_features_allowed"] is False

def test_no_sample_match_identity_leak():
    src = (SRC / "canonical_event_lite.py").read_text(encoding="utf-8")
    for token in ["Australia", "Turkey", "World Cup", "13.06.2026", "77798", "6935"]:
        assert token not in src



def test_xml_group_text_fields_feed_canonical_candidates(tmp_path):
    p = tmp_path / "Players.xml"
    p.write_text(
        "<file><ALL_INSTANCES><instance><ID>9</ID><start>100</start><end>101.5</end>"
        "<label><group>Team</group><text>Alpha</text></label>"
        "<label><group>Half</group><text>2</text></label>"
        "<label><group>Action</group><text>Pass</text></label>"
        "<label><group>pos_x</group><text>80</text></label>"
        "<label><group>pos_y</group><text>40</text></label>"
        "</instance></ALL_INSTANCES></file>", encoding="utf-8")
    rows, _ = read_xml_rows(p)
    assert rows[0]["Half"] == "2"
    assert rows[0]["Action"] == "Pass"
    match = tmp_path / "runtime/active_single_match/current"
    match.mkdir(parents=True)
    (match / "Players.xml").write_text(p.read_text(encoding="utf-8"), encoding="utf-8")
    canonical, audit = build_canonical_lite(match)
    assert canonical[0]["period_candidate"] == "SECOND_HALF"
    assert canonical[0]["event_type_raw"] == "Pass"
    assert canonical[0]["x_meters"] == 80.0
    assert canonical[0]["y_meters"] == 40.0
    assert audit["coverage"]["period_rows"] == 1


def test_fixed_frame_names_do_not_claim_attacking_direction(tmp_path):
    rows, audit = build_canonical_lite(make_match(tmp_path))
    forbidden = {"DEFENSIVE_THIRD", "MIDDLE_THIRD", "FINAL_THIRD", "LEFT_CHANNEL", "RIGHT_CHANNEL"}
    assert all(row.get("fixed_x_band") not in forbidden for row in rows)
    assert all(row.get("fixed_y_band") not in forbidden for row in rows)
    assert audit["zone_semantics"] == "FIXED_PITCH_FRAME_ONLY_NOT_ATTACKING_ORIENTATION"


def test_xlsx_is_explicit_aggregate_validation(tmp_path):
    rows, audit = build_canonical_lite(make_match(tmp_path))
    xlsx = [row for row in rows if row["source_format"] == "xlsx"]
    assert xlsx
    assert all(row["row_surface_class"] == "AGGREGATE_VALIDATION" for row in xlsx)
    assert all(row["event_family"] == "AGGREGATE_VALIDATION_ROW" for row in xlsx)
    assert "AGGREGATE_VALIDATION_ROW" not in audit["event_family_volume"]
