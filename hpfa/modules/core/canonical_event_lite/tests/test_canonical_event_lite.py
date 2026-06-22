import json
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "canonical_event_lite" / "src"
sys.path.insert(0, str(SRC))

from canonical_event_lite import build_canonical_lite, read_xml_rows, write_outputs


def write_xlsx(path: Path):
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr(
            "xl/sharedStrings.xml",
            "<sst><si><t>Team</t></si><si><t>Action</t></si><si><t>x</t></si><si><t>y</t></si><si><t>Turkey</t></si><si><t>Pass</t></si></sst>",
        )
        zf.writestr(
            "xl/worksheets/sheet1.xml",
            "<worksheet><sheetData>"
            "<row><c t='s'><v>0</v></c><c t='s'><v>1</v></c><c t='s'><v>2</v></c><c t='s'><v>3</v></c></row>"
            "<row><c t='s'><v>4</v></c><c t='s'><v>5</v></c><c><v>20</v></c><c><v>30</v></c></row>"
            "</sheetData></worksheet>",
        )


def make_active_match(tmp_path: Path) -> Path:
    match = tmp_path / "runtime" / "active_single_match" / "current"
    match.mkdir(parents=True)
    (match / "Players.csv").write_text("Team;Action;x;y\nTurkey;Pass;20;30\nAustralia;Shot;80;40\n", encoding="utf-8")
    (match / "Teams.csv").write_text("Team,Action,x,y\nTurkey,Goal Kick Short,10,10\n", encoding="utf-8")
    (match / "Goalkeepers.csv").write_text("Team|Action|x|y\nTurkey|Restart|5|34\n", encoding="utf-8")
    xml = "<root><instance team='Turkey' action='Duel' x='55' y='20'/><event><team>Australia</team><action>Recovery</action><x>40</x><y>50</y></event></root>"
    (match / "Players.xml").write_text(xml, encoding="utf-8")
    (match / "Teams.xml").write_text(xml, encoding="utf-8")
    (match / "Goalkeepers.xml").write_text(xml, encoding="utf-8")
    write_xlsx(match / "Players.xlsx")
    write_xlsx(match / "Goalkeepers.xlsx")
    return match


def test_canonical_event_lite_reads_csv_xml_xlsx_and_writes_outputs(tmp_path):
    match = make_active_match(tmp_path)
    out = tmp_path / "HPFA"

    audit = write_outputs(match, out, root=ROOT)

    assert audit["status"] == "PASS"
    assert audit["canonical_event_count"] == "UNKNOWN"
    assert audit["canonical_lite_row_count"] >= 12
    assert audit["coverage"]["coordinate_rows"] >= 8
    assert (out / "canonical_event_lite_v1.json").exists()
    assert (out / "canonical_event_lite_v1.tsv").exists()
    assert (out / "canonical_event_lite_audit_v1.json").exists()
    assert (out / "canonical_event_lite_audit_v1.txt").exists()
    assert not any(p.is_dir() for p in out.iterdir())


def test_xml_reader_flattens_attributes_and_child_text(tmp_path):
    p = tmp_path / "sample.xml"
    p.write_text("<root><instance team='Turkey' action='Pass'><x>25</x><y>30</y></instance></root>", encoding="utf-8")

    rows, headers = read_xml_rows(p)

    assert rows[0]["team"] == "Turkey"
    assert rows[0]["action"] == "Pass"
    assert rows[0]["x"] == "25"
    assert rows[0]["y"] == "30"
    assert "team" in headers


def test_nested_phone_output_directory_is_rejected(tmp_path):
    match = make_active_match(tmp_path)
    with pytest.raises(ValueError, match="nested_phone_output_directory_rejected"):
        write_outputs(match, "/sdcard/Download/HPFA/p2", root=ROOT)


def test_canonical_lite_preserves_claim_boundary(tmp_path):
    match = make_active_match(tmp_path)
    rows, audit = build_canonical_lite(match)

    assert audit["canonical_event_count"] == "UNKNOWN"
    assert rows
    assert all(row["row_claim_safety"] == "EVIDENCE_ONLY" for row in rows)
    assert "PASS" in audit["event_family_volume"]
    assert audit["zone_distribution"].get("UNKNOWN", {}).get("pct", 0.0) < 100.0
