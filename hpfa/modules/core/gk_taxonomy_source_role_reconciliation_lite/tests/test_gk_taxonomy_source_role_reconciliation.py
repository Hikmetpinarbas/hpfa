import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "gk_taxonomy_source_role_reconciliation_lite" / "src"
sys.path.insert(0, str(SRC))

from gk_taxonomy_source_role_reconciliation import build_reconciliation


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def identity_review_payload(source_roles):
    return {"status": "REVIEW_REQUIRED", "review_candidates": [{"cluster_id": "abc123", "source_roles": source_roles, "source_row_count": 7}]}


def test_missing_identity_review_fail_closed(tmp_path):
    report = build_reconciliation(tmp_path, root=ROOT)
    assert report["status"] == "FAIL_CLOSED"
    assert report["decision"] == "FAIL_CLOSED_NO_IDENTITY_REVIEW"


def test_fail_closed_identity_review_input_does_not_clear(tmp_path):
    write_json(tmp_path / "identity_review_resolution_lite_v1.json", {"status": "FAIL_CLOSED", "decision": "FAIL_CLOSED_NO_IDENTITY_GATE", "review_candidates": []})
    report = build_reconciliation(tmp_path, root=ROOT)
    assert report["status"] == "FAIL_CLOSED"
    assert report["decision"] == "FAIL_CLOSED_IDENTITY_REVIEW_INPUT"
    assert report["downstream_gate"]["identity_review_resolution"] == "WAIT"


def test_no_gk_player_overlap_passes_review_clearance(tmp_path):
    write_json(tmp_path / "identity_review_resolution_lite_v1.json", identity_review_payload(["teams", "players"]))
    report = build_reconciliation(tmp_path, root=ROOT)
    assert report["status"] == "PASS"
    assert report["decision"] == "NO_GK_PLAYER_OVERLAP_DETECTED"


def test_gk_player_overlap_remains_review_required(tmp_path):
    write_json(tmp_path / "identity_review_resolution_lite_v1.json", identity_review_payload(["goalkeepers", "players"]))
    report = build_reconciliation(tmp_path, root=ROOT)
    assert report["status"] == "REVIEW_REQUIRED"
    assert report["decision"] == "GK_PLAYER_ROLE_OVERLAP_REVIEW_REQUIRED"
    assert report["gk_player_overlap_cluster_count"] == 1
    assert report["gk_player_overlap_row_count"] == 7


def test_no_role_or_event_truth_claims(tmp_path):
    write_json(tmp_path / "identity_review_resolution_lite_v1.json", identity_review_payload(["goalkeepers", "players"]))
    report = build_reconciliation(tmp_path, root=ROOT)
    assert report["canonical_event_count"] == "UNKNOWN"
    assert report["deduplicated_event_count"] == "UNKNOWN"
    assert report["source_role_truth"] is False
    assert report["gk_taxonomy_truth"] is False
    assert report["event_count_claim_allowed"] is False
