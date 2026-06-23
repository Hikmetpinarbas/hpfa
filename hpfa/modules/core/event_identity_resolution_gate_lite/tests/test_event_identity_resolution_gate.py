import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "event_identity_resolution_gate_lite" / "src"
sys.path.insert(0, str(SRC))

from event_identity_resolution_gate import build_gate, v0_exact_fingerprint, v1_bucketed_fingerprint, write_outputs


def test_v0_exact_fingerprint_groups_exact_candidates(tmp_path):
    rows = {"rows": [
        {"source_role": "players", "source_format": "csv", "source_file": "Players.csv", "source_row_index": 1, "event_family": "PASS", "team_normalized": "Alpha (1)", "player_raw": "Player One", "x_meters": 50, "y_meters": 20},
        {"source_role": "teams", "source_format": "csv", "source_file": "Teams.csv", "source_row_index": 7, "event_family": "PASS", "team_normalized": "Alpha", "player_raw": "Player One", "x_meters": 50, "y_meters": 20},
    ]}
    path = tmp_path / "canonical_event_lite_v1.json"
    path.write_text(json.dumps(rows), encoding="utf-8")

    report = build_gate(path)

    assert report["status"] == "PASS"
    assert report["candidate_cluster_count"] >= 1
    assert report["duplicate_cluster_candidates"][0]["cross_surface"] is True
    assert report["deduplicated_event_count"] == "UNKNOWN"
    assert report["event_count_claim_allowed"] is False
    assert report["metric_count_allowed"] is False


def test_v1_bucketed_fingerprint_groups_near_candidates(tmp_path):
    rows = {"rows": [
        {"source_role": "players", "source_format": "csv", "source_file": "Players.csv", "source_row_index": 1, "event_family": "SHOT", "team_normalized": "Beta", "player_raw": "Player Two", "x_meters": 80.1, "y_meters": 30.2},
        {"source_role": "teams", "source_format": "csv", "source_file": "Teams.csv", "source_row_index": 9, "event_family": "SHOT", "team_normalized": "Beta", "player_raw": "Player Two", "x_meters": 84.8, "y_meters": 34.7},
    ]}
    path = tmp_path / "canonical_event_lite_v1.json"
    path.write_text(json.dumps(rows), encoding="utf-8")

    report = build_gate(path)

    assert any(c["strategy"] == "V1_BUCKETED_SPATIOTEMPORAL_FINGERPRINT" for c in report["duplicate_cluster_candidates"])
    assert report["canonical_event_count"] == "UNKNOWN"


def test_v2_preserves_cross_surface_provenance(tmp_path):
    rows = {"rows": [
        {"source_role": "players", "source_format": "csv", "source_file": "Players.csv", "source_row_index": 1, "event_family": "PASS", "team_normalized": "Alpha", "player_raw": "Player One", "x_meters": 10, "y_meters": 10},
        {"source_role": "teams", "source_format": "csv", "source_file": "Teams.csv", "source_row_index": 2, "event_family": "PASS", "team_normalized": "Alpha", "player_raw": "Player One", "x_meters": 10, "y_meters": 10},
    ]}
    path = tmp_path / "canonical_event_lite_v1.json"
    path.write_text(json.dumps(rows), encoding="utf-8")

    report = build_gate(path)
    cluster = report["duplicate_cluster_candidates"][0]

    assert len(cluster["provenance"]) == 2
    assert {p["source_role"] for p in cluster["provenance"]} == {"players", "teams"}
    assert cluster["deduplicated_event_truth"] is False
    assert cluster["metric_count_allowed"] is False


def test_v3_missing_fields_fail_closed(tmp_path):
    rows = {"rows": [
        {"source_role": "players", "source_file": "Players.xml", "source_row_index": 1, "event_family": "UNKNOWN_OR_OTHER"}
    ]}
    path = tmp_path / "canonical_event_lite_v1.json"
    path.write_text(json.dumps(rows), encoding="utf-8")

    report = build_gate(path)

    assert report["decision"] == "UNRESOLVED_INSUFFICIENT_FIELDS"
    assert report["candidate_cluster_count"] == 0
    assert report["unresolved_candidate_count"] == 1
    assert report["deduplicated_event_count"] == "UNKNOWN"


def test_write_outputs_flat_and_no_count_unlock(tmp_path):
    rows = {"rows": [
        {"source_role": "players", "source_file": "Players.csv", "source_row_index": 1, "event_family": "PASS", "team_normalized": "Alpha", "player_raw": "One", "x_meters": 30, "y_meters": 30},
        {"source_role": "teams", "source_file": "Teams.csv", "source_row_index": 2, "event_family": "PASS", "team_normalized": "Alpha", "player_raw": "One", "x_meters": 30, "y_meters": 30},
    ]}
    path = tmp_path / "canonical_event_lite_v1.json"
    path.write_text(json.dumps(rows), encoding="utf-8")
    out = tmp_path / "HPFA"

    report = write_outputs(path, out, root=ROOT)

    assert report["status"] == "PASS"
    assert (out / "event_identity_resolution_gate_lite_v1.json").exists()
    assert (out / "event_identity_resolution_gate_lite_v1.txt").exists()
    assert report["event_count_claim_allowed"] is False
    assert report["metric_count_allowed"] is False
    assert not any(p.is_dir() for p in out.iterdir())


def test_nested_phone_output_directory_is_rejected(tmp_path):
    path = tmp_path / "canonical_event_lite_v1.json"
    path.write_text(json.dumps({"rows": []}), encoding="utf-8")
    with pytest.raises(ValueError, match="nested_phone_output_directory_rejected"):
        write_outputs(path, "/sdcard/Download/HPFA/event-id", root=ROOT)


def test_no_sample_match_identity_leak():
    src = (SRC / "event_identity_resolution_gate.py").read_text(encoding="utf-8")
    forbidden = ["Australia", "Turkey", "World Cup", "13.06.2026", "77798", "6935"]
    for token in forbidden:
        assert token not in src
