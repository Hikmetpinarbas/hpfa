import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "reporting" / "postmatch_analyst_report_lite" / "src"
sys.path.insert(0, str(SRC))

from postmatch_analyst_report import build_report, write_outputs


def write_json(path: Path, obj):
    path.write_text(json.dumps(obj), encoding="utf-8")


def sample_team_audit():
    return {
        "team_entities": [
            {
                "display_label_candidate": "Team A Label",
                "team_entity_key": "TEAM_A_KEY",
                "visible_rows": 100,
                "event_family_volume": {"PASS": 50, "SHOT": 10, "DUEL_PRESSURE": 5, "GOALKEEPER_RESTART": 1},
                "zone_distribution": {"FINAL_THIRD": 40, "MIDDLE_THIRD": 40, "DEFENSIVE_THIRD": 20},
                "channel_distribution": {"RIGHT_CHANNEL": 45, "CENTRAL_CHANNEL": 35, "LEFT_CHANNEL": 20},
            },
            {
                "display_label_candidate": "Team B Label",
                "team_entity_key": "TEAM_B_KEY",
                "visible_rows": 50,
                "event_family_volume": {"PASS": 20, "SHOT": 5, "DUEL_PRESSURE": 10, "GOALKEEPER_RESTART": 5},
                "zone_distribution": {"FINAL_THIRD": 10, "MIDDLE_THIRD": 20, "DEFENSIVE_THIRD": 20},
                "channel_distribution": {"RIGHT_CHANNEL": 10, "CENTRAL_CHANNEL": 25, "LEFT_CHANNEL": 15},
            },
        ]
    }


def test_builds_numeric_team_and_action_comparisons(tmp_path):
    out = tmp_path / "HPFA"
    out.mkdir()
    write_json(out / "team_binding_lite_audit_v1.json", sample_team_audit())
    write_json(out / "primary_event_surface_gate_lite_v1.json", {"decision": "UNRESOLVED_REVIEW_REQUIRED", "primary_event_surface_candidate": "UNRESOLVED"})

    report = build_report(out)

    assert report["status"] == "PASS"
    assert report["team_comparison"]["left_team"] == "Team A Label"
    assert report["team_comparison"]["right_team"] == "Team B Label"
    assert report["team_comparison"]["left_visible_rows"] == 100
    assert report["team_comparison"]["right_visible_rows"] == 50
    assert report["team_comparison"]["row_ratio_left_to_right"] == 2.0
    pass_row = next(r for r in report["action_family_comparison"] if r["metric"] == "PASS")
    assert pass_row["diff_left_minus_right"] == 30


def test_includes_plain_analyst_translation(tmp_path):
    out = tmp_path / "HPFA"
    out.mkdir()
    write_json(out / "team_binding_lite_audit_v1.json", sample_team_audit())

    report = build_report(out)

    translation = report["analyst_translation"]
    assert translation
    assert any("yaklaşık 2.0 katı" in item for item in translation)
    assert any("pas hacmi" in item for item in translation)
    assert any("Analyst conclusion" in item for item in translation)


def test_falls_back_to_team_entity_key_when_display_label_missing(tmp_path):
    out = tmp_path / "HPFA"
    out.mkdir()
    audit = sample_team_audit()
    for row in audit["team_entities"]:
        row.pop("display_label_candidate")
    write_json(out / "team_binding_lite_audit_v1.json", audit)

    report = build_report(out)

    assert report["team_comparison"]["left_team"] == "TEAM_A_KEY"
    assert report["team_comparison"]["right_team"] == "TEAM_B_KEY"


def test_preserves_metric_locks(tmp_path):
    out = tmp_path / "HPFA"
    out.mkdir()
    write_json(out / "team_binding_lite_audit_v1.json", sample_team_audit())
    write_json(out / "metric_family_registry_lite_v1.json", {"registry_record_count": 34, "metric_value_output_allowed": False, "efficiency_calculation_allowed": False})

    report = build_report(out)

    assert report["metric_registry_summary"]["metric_value_output_allowed"] is False
    assert report["metric_registry_summary"]["efficiency_calculation_allowed"] is False


def test_includes_physical_report_summary(tmp_path):
    out = tmp_path / "HPFA"
    out.mkdir()
    write_json(out / "team_binding_lite_audit_v1.json", sample_team_audit())
    write_json(out / "physical_cost_surface_audit_v1.json", {"record_count": 323, "surface_counts": {"PHYSICAL_COST_SURFACE": 255, "REPORT_METRIC_SURFACE": 68}})

    report = build_report(out)

    assert report["physical_report_summary"]["record_count"] == 323
    assert report["physical_report_summary"]["surface_counts"]["PHYSICAL_COST_SURFACE"] == 255


def test_write_outputs_flat_files(tmp_path):
    out = tmp_path / "HPFA"
    out.mkdir()
    write_json(out / "team_binding_lite_audit_v1.json", sample_team_audit())

    report = write_outputs(out, root=ROOT)
    txt = (out / "postmatch_analyst_report_lite_v1.txt").read_text(encoding="utf-8")

    assert report["status"] == "PASS"
    assert (out / "postmatch_analyst_report_lite_v1.json").exists()
    assert (out / "postmatch_analyst_report_lite_v1.txt").exists()
    assert "[analyst_translation]" in txt
    assert not any(p.is_dir() for p in out.iterdir())


def test_nested_phone_output_directory_is_rejected():
    with pytest.raises(ValueError, match="nested_phone_output_directory_rejected"):
        write_outputs("/sdcard/Download/HPFA/postmatch", root=ROOT)


def test_no_literal_match_identity_leak():
    src = (SRC / "postmatch_analyst_report.py").read_text(encoding="utf-8")
    for token in ["World Cup", "13.06.2026"]:
        assert token not in src
