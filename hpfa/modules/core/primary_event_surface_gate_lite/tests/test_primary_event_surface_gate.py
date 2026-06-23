import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "primary_event_surface_gate_lite" / "src"
sys.path.insert(0, str(SRC))

from primary_event_surface_gate import evaluate, write_outputs


def write_json(path: Path, obj):
    path.write_text(json.dumps(obj), encoding="utf-8")


def surface(source_file, role, fmt, rows, event_rows, team_rows, coord_rows, missing=None):
    return {
        "source_file": source_file,
        "source_role": role,
        "source_format": fmt,
        "rows_read": rows,
        "event_type_coverage_rows": event_rows,
        "team_coverage_rows": team_rows,
        "coordinate_coverage_rows": coord_rows,
        "missing_column_families": missing or [],
    }


def test_selects_players_csv_as_primary_candidate(tmp_path):
    audit = {
        "files_read": [
            surface("Players.csv", "players", "csv", 100, 100, 100, 100, ["minute", "timestamp"]),
            surface("Teams.csv", "teams", "csv", 100, 100, 0, 100, ["team", "player", "minute", "timestamp"]),
            surface("Players.xlsx", "players", "xlsx", 30, 0, 30, 0, ["event_type", "x", "y"]),
        ]
    }
    audit_path = tmp_path / "canonical_event_lite_audit_v1.json"
    write_json(audit_path, audit)

    report = evaluate(audit_path)

    assert report["status"] == "PASS"
    assert report["primary_event_surface_candidate"] == "Players.csv"
    assert report["primary_event_surface_candidate_role"] == "players"
    assert report["event_count_claim_allowed"] is False
    assert report["deduplicated_event_count"] == "UNKNOWN"


def test_excludes_xlsx_aggregate_surfaces(tmp_path):
    audit = {"files_read": [surface("Players.xlsx", "players", "xlsx", 30, 0, 30, 0)]}
    audit_path = tmp_path / "canonical_event_lite_audit_v1.json"
    write_json(audit_path, audit)

    report = evaluate(audit_path)

    assert report["decision"] == "UNRESOLVED_REVIEW_REQUIRED"
    assert report["eligible_candidate_count"] == 0
    assert report["candidate_evaluations"][0]["aggregate_surface_flag"] is True


def test_duplicate_risk_keeps_review_boundary(tmp_path):
    audit = {"files_read": [surface("Players.csv", "players", "csv", 100, 100, 100, 100)]}
    identity = {"decision": "DUPLICATE_RISK_CANDIDATES_FOUND", "candidate_cluster_count": 5, "duplicate_risk_candidate_count": 12}
    audit_path = tmp_path / "canonical_event_lite_audit_v1.json"
    identity_path = tmp_path / "event_identity_resolution_gate_lite_v1.json"
    write_json(audit_path, audit)
    write_json(identity_path, identity)

    report = evaluate(audit_path, identity_path)

    assert report["decision"] == "CANDIDATE_SELECTED_WITH_DUPLICATE_RISK_REVIEW"
    assert report["duplicate_risk_summary"]["candidate_cluster_count"] == 5
    assert report["event_count_claim_allowed"] is False


def test_physical_cost_surface_does_not_influence_candidate(tmp_path):
    audit = {"files_read": [surface("Teams.csv", "teams", "csv", 100, 100, 0, 100)]}
    physical = {"record_count": 323, "surface_counts": {"PHYSICAL_COST_SURFACE": 255, "REPORT_METRIC_SURFACE": 68}, "runtime_event_truth": False}
    audit_path = tmp_path / "canonical_event_lite_audit_v1.json"
    physical_path = tmp_path / "physical_cost_surface_audit_v1.json"
    write_json(audit_path, audit)
    write_json(physical_path, physical)

    report = evaluate(audit_path, physical_cost_audit_json=physical_path)

    assert report["physical_cost_surface_summary"]["record_count"] == 323
    assert report["primary_event_surface_candidate"] == "Teams.csv"
    assert report["event_count_claim_allowed"] is False
    assert report["metric_count_allowed"] is False


def test_write_outputs_flat_files(tmp_path):
    out = tmp_path / "HPFA"
    out.mkdir()
    write_json(out / "canonical_event_lite_audit_v1.json", {"files_read": [surface("Players.csv", "players", "csv", 100, 100, 100, 100)]})
    write_json(out / "event_identity_resolution_gate_lite_v1.json", {"candidate_cluster_count": 0, "duplicate_risk_candidate_count": 0})
    write_json(out / "physical_cost_surface_audit_v1.json", {"record_count": 3, "runtime_event_truth": False})

    report = write_outputs(out, root=ROOT)

    assert report["status"] == "PASS"
    assert (out / "primary_event_surface_gate_lite_v1.json").exists()
    assert (out / "primary_event_surface_gate_lite_v1.txt").exists()
    assert not any(p.is_dir() for p in out.iterdir())


def test_nested_phone_output_directory_is_rejected():
    with pytest.raises(ValueError, match="nested_phone_output_directory_rejected"):
        write_outputs("/sdcard/Download/HPFA/primary-event", root=ROOT)


def test_no_sample_match_identity_leak():
    src = (SRC / "primary_event_surface_gate.py").read_text(encoding="utf-8")
    forbidden = ["Australia", "Turkey", "World Cup", "13.06.2026", "77798", "6935"]
    for token in forbidden:
        assert token not in src
