import csv
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "event_state_transition_verifier_lite" / "src"
sys.path.insert(0, str(SRC))

from event_state_transition_verifier import build_report, write_outputs


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def write_csv(path: Path, values):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["event_type"])
        writer.writeheader()
        for value in values:
            writer.writerow({"event_type": value})


def clear_gates(tmp_path):
    write_json(tmp_path / "primary_surface_review_resolution_lite_v1.json", {"status": "PASS", "decision": "RESOLVED_CANDIDATE_FOR_DOWNSTREAM_REVIEW"})
    write_json(tmp_path / "identity_review_resolution_lite_v1.json", {"status": "PASS", "decision": "NO_IDENTITY_OVERLAP_DETECTED"})
    write_json(tmp_path / "gk_taxonomy_source_role_reconciliation_lite_v1.json", {"status": "PASS", "decision": "NO_GK_PLAYER_OVERLAP_DETECTED"})


def test_missing_inputs_fail_closed(tmp_path):
    report = build_report(tmp_path, root=ROOT)
    assert report["status"] == "FAIL_CLOSED"
    assert report["decision"] == "FAIL_CLOSED_MISSING_INPUTS"


def test_upstream_review_blocker_waits(tmp_path):
    write_json(tmp_path / "primary_surface_review_resolution_lite_v1.json", {"status": "REVIEW_REQUIRED", "decision": "UNRESOLVED_SOURCE_CONFLICTS_REMAIN"})
    write_json(tmp_path / "identity_review_resolution_lite_v1.json", {"status": "PASS", "decision": "NO_IDENTITY_OVERLAP_DETECTED"})
    write_json(tmp_path / "gk_taxonomy_source_role_reconciliation_lite_v1.json", {"status": "PASS", "decision": "NO_GK_PLAYER_OVERLAP_DETECTED"})
    report = build_report(tmp_path, root=ROOT)
    assert report["status"] == "REVIEW_REQUIRED"
    assert report["decision"] == "WAIT_UPSTREAM_REVIEW_BLOCKERS"


def test_no_event_surface_available(tmp_path):
    clear_gates(tmp_path)
    write_json(tmp_path / "primary_event_surface_gate_lite_v1.json", {"top_candidate_for_review": {"source_file": "missing.csv"}})
    report = build_report(tmp_path, root=ROOT)
    assert report["decision"] == "NO_EVENT_SURFACE_AVAILABLE"
    assert report["rows_evaluated"] == 0


def test_no_transition_issues_detected(tmp_path):
    clear_gates(tmp_path)
    write_json(tmp_path / "primary_event_surface_gate_lite_v1.json", {"top_candidate_for_review": {"source_file": "surface.csv"}})
    write_csv(tmp_path / "surface.csv", ["Pass", "Carry", "Recovery"])
    report = build_report(tmp_path, root=ROOT)
    assert report["status"] == "PASS"
    assert report["decision"] == "NO_TRANSITION_ISSUES_DETECTED"


def test_shot_terminal_continuation_review_required(tmp_path):
    clear_gates(tmp_path)
    write_json(tmp_path / "primary_event_surface_gate_lite_v1.json", {"top_candidate_for_review": {"source_file": "surface.csv"}})
    write_csv(tmp_path / "surface.csv", ["Shot", "Pass"])
    report = build_report(tmp_path, root=ROOT)
    assert report["status"] == "REVIEW_REQUIRED"
    assert report["decision"] == "TRANSITION_REVIEW_REQUIRED"
    assert report["transition_issues"][0]["issue_class"] == "illegal_continuation_after_shot_terminal"


def test_no_truth_claims(tmp_path):
    report = build_report(tmp_path, root=ROOT)
    assert report["canonical_event_count"] == "UNKNOWN"
    assert report["deduplicated_event_count"] == "UNKNOWN"
    assert report["event_state_truth"] is False
    assert report["phase_truth"] is False
    assert report["possession_truth"] is False
    assert report["sequence_truth"] is False


def test_flat_outputs_and_nested_rejection(tmp_path):
    clear_gates(tmp_path)
    out = tmp_path / "HPFA"
    out.mkdir()
    report = write_outputs(tmp_path, out, root=ROOT)
    assert (out / "event_state_transition_verifier_lite_v1.json").exists()
    assert (out / "event_state_transition_verifier_lite_v1.txt").exists()
    assert report["status"] == "REVIEW_REQUIRED"
    with pytest.raises(ValueError, match="nested_phone_output_directory_rejected"):
        write_outputs(tmp_path, "/sdcard/Download/HPFA/event-state", root=ROOT)


def test_no_sample_match_identity_leak():
    src = (SRC / "event_state_transition_verifier.py").read_text(encoding="utf-8")
    contract = (ROOT / "docs" / "contracts" / "event_state_transition_verifier_lite_v1.md").read_text(encoding="utf-8")
    for token in ["Turkey", "Australia", "Türkiye", "Avustralya", "Juventus", "World Cup", "13.06.2026"]:
        assert token not in src
        assert token not in contract
