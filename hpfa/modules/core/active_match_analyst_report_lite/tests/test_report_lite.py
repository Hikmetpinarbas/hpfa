import json
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "active_match_analyst_report_lite" / "src"
sys.path.insert(0, str(SRC))

from report_lite import OUTPUT_JSON, OUTPUT_TXT, build_report, write_report


FORBIDDEN_OUTPUT_STRINGS = [
    "team dominated",
    "coach planned",
    "pitch control truth",
    "off-ball structure truth",
    "body orientation truth",
    "fatigue truth",
    "control was lost",
    "opponent dictated",
]


def write_csv(path: Path, body: str):
    path.write_text(body, encoding="utf-8")


def write_xml(path: Path):
    path.write_text("<root><instance/><instance/></root>", encoding="utf-8")


def write_xlsx(path: Path):
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("xl/worksheets/sheet1.xml", "<worksheet><sheetData><row/><row/></sheetData></worksheet>")


def make_active_match(tmp_path: Path) -> Path:
    match = tmp_path / "runtime" / "active_single_match" / "current"
    match.mkdir(parents=True)
    write_csv(
        match / "Players.csv",
        "Team,Action,x,y\nTurkey,Pass,20,20\nTurkey,Shot,80,30\nAustralia,Ball Loss,65,50\n",
    )
    write_csv(
        match / "Teams.csv",
        "Team,Action,x,y\nTurkey,Goal Kick Short,10,10\nAustralia,Duel,60,45\n",
    )
    write_csv(
        match / "Goalkeepers.csv",
        "Team,Action,x,y\nTurkey,Restart,5,34\n",
    )
    write_xml(match / "Players.xml")
    write_xml(match / "Teams.xml")
    write_xml(match / "Goalkeepers.xml")
    write_xlsx(match / "Players.xlsx")
    write_xlsx(match / "Goalkeepers.xlsx")
    return match


def test_report_lite_writes_flat_json_and_txt_outputs(tmp_path):
    match = make_active_match(tmp_path)
    out = tmp_path / "HPFA"

    result = write_report(match, out, root=ROOT)

    assert result["status"] == "PASS"
    assert result["canonical_event_count"] == "UNKNOWN"
    assert (out / OUTPUT_JSON).exists()
    assert (out / OUTPUT_TXT).exists()
    assert not any(p.is_dir() for p in out.iterdir())

    data = json.loads((out / OUTPUT_JSON).read_text(encoding="utf-8"))
    assert data["key_action_blocks"]["PASS"] == 1
    assert data["key_action_blocks"]["SHOT"] == 1
    assert data["key_action_blocks"]["BALL_LOSS"] == 1
    assert data["key_action_blocks"]["GOALKEEPER_RESTART"] == 2
    assert data["team_row_volume"]["Turkey"] == 2


def test_nested_phone_output_directory_is_rejected(tmp_path):
    match = make_active_match(tmp_path)
    with pytest.raises(ValueError, match="nested_phone_output_directory_rejected"):
        write_report(match, "/sdcard/Download/HPFA/p1", root=ROOT)


def test_report_preserves_row_level_language_and_unknown_canonical_count(tmp_path):
    match = make_active_match(tmp_path)
    out = tmp_path / "HPFA"
    write_report(match, out, root=ROOT)
    text = (out / OUTPUT_TXT).read_text(encoding="utf-8")

    assert "canonical_event_count=UNKNOWN" in text
    assert "visible row-level evidence" in text or "row-level" in text
    for forbidden in FORBIDDEN_OUTPUT_STRINGS:
        assert forbidden not in text.lower()


def test_missing_columns_are_reported_not_crashed(tmp_path):
    match = make_active_match(tmp_path)
    write_csv(match / "Players.csv", "foo,bar\n1,2\n")

    report = build_report(match, root=ROOT)

    assert report["status"] == "PASS"
    assert report["missing_column_report"]
    players_missing = [r for r in report["missing_column_report"] if r["source_file"] == "Players.csv"]
    assert players_missing
    assert "action" in players_missing[0]["missing_column_family"]
