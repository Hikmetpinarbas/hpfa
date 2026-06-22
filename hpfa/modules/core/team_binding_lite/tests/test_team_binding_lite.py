import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "team_binding_lite" / "src"
sys.path.insert(0, str(SRC))

from team_binding_lite import build_team_binding, split_team_label, write_outputs


def test_split_team_label_preserves_external_id():
    label, ext = split_team_label("Alpha FC (1001)")
    assert label == "Alpha FC"
    assert ext == "1001"


def test_team_binding_merges_aliases_and_reports_unresolved():
    rows = [
        {"team_normalized": "Alpha FC (1001)", "event_family": "PASS", "zone": "FINAL_THIRD", "channel": "RIGHT_CHANNEL", "source_file": "Teams.csv", "source_format": "csv"},
        {"team_normalized": "Alpha FC", "event_family": "SHOT", "zone": "FINAL_THIRD", "channel": "CENTRAL_CHANNEL", "source_file": "Players.csv", "source_format": "csv"},
        {"team_normalized": "Beta FC (2002)", "event_family": "PASS", "zone": "MIDDLE_THIRD", "channel": "LEFT_CHANNEL", "source_file": "Teams.csv", "source_format": "csv"},
        {"team_normalized": None, "event_family": "PASS", "source_file": "Teams.xml", "source_row_index": 4},
    ]
    report = build_team_binding(rows)

    assert report["status"] == "PASS"
    assert report["canonical_event_count"] == "UNKNOWN"
    assert report["team_entity_count"] == 2
    assert report["unresolved_team_rows"] == 1
    alpha = next(row for row in report["team_entities"] if row["team_entity_key"] == "alpha_fc")
    assert alpha["visible_rows"] == 2
    assert alpha["external_ids"] == ["1001"]
    assert set(alpha["aliases"]) == {"Alpha FC (1001)", "Alpha FC"}


def test_team_binding_writes_flat_outputs(tmp_path):
    rows_path = tmp_path / "canonical_event_lite_v1.json"
    rows_path.write_text(json.dumps({"rows": [
        {"team_normalized": "Alpha FC (1001)", "player_raw": "Player One", "source_file": "Players.csv", "source_format": "csv", "event_family": "PASS"}
    ]}), encoding="utf-8")
    out = tmp_path / "HPFA"

    report = write_outputs(rows_path, out, root=ROOT)

    assert report["status"] == "PASS"
    assert (out / "team_binding_lite_v1.json").exists()
    assert (out / "team_binding_lite_audit_v1.json").exists()
    assert (out / "team_binding_lite_audit_v1.txt").exists()
    assert not any(p.is_dir() for p in out.iterdir())


def test_nested_phone_output_directory_is_rejected(tmp_path):
    rows_path = tmp_path / "canonical_event_lite_v1.json"
    rows_path.write_text(json.dumps({"rows": []}), encoding="utf-8")
    with pytest.raises(ValueError, match="nested_phone_output_directory_rejected"):
        write_outputs(rows_path, "/sdcard/Download/HPFA/team-binding", root=ROOT)


def test_no_sample_match_identity_leak():
    src = (SRC / "team_binding_lite.py").read_text(encoding="utf-8")
    forbidden = [
        "Australia",
        "Turkey",
        "World Cup",
        "13.06.2026",
        "77798",
        "6935",
    ]
    for token in forbidden:
        assert token not in src
