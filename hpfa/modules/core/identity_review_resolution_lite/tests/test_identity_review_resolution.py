import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "identity_review_resolution_lite" / "src"
sys.path.insert(0, str(SRC))

from identity_review_resolution import build_resolution, write_outputs


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def identity_payload(clusters=1, rows=2, unresolved=0):
    return {
        "module_id": "event_identity_resolution_gate_lite_v1",
        "status": "PASS",
        "decision": "DUPLICATE_RISK_CANDIDATES_FOUND" if clusters else "UNRESOLVED_INSUFFICIENT_FIELDS" if unresolved else "NO_DUPLICATE_RISK_CANDIDATES",
        "claim_safety": "DUPLICATE_RISK_CANDIDATES_ONLY",
        "candidate_cluster_count": clusters,
        "duplicate_risk_candidate_count": rows,
        "unresolved_candidate_count": unresolved,
        "duplicate_cluster_candidates": [
            {
                "cluster_id": "abc123",
                "strategy": "V1_BUCKETED_SPATIOTEMPORAL_FINGERPRINT",
                "duplicate_risk_level": "MEDIUM",
                "source_roles": ["players", "teams"],
                "source_row_count": rows,
                "review_reason": "cross_surface_rows_share_candidate_fingerprint",
                "provenance": [{"source_file": "Rows.csv", "source_role": "players", "source_row_index": 7}],
            }
        ] if clusters else [],
        "canonical_event_count": "UNKNOWN",
        "deduplicated_event_count": "UNKNOWN",
        "event_count_claim_allowed": False,
    }


def test_missing_identity_gate_fail_closed(tmp_path):
    report = build_resolution(tmp_path, root=ROOT)
    assert report["status"] == "FAIL_CLOSED"
    assert report["decision"] == "FAIL_CLOSED_NO_IDENTITY_GATE"
    assert report["deduplicated_event_count"] == "UNKNOWN"


def test_no_overlap_detected_allows_review_clearance(tmp_path):
    write_json(tmp_path / "event_identity_resolution_gate_lite_v1.json", identity_payload(clusters=0, rows=0, unresolved=0))
    report = build_resolution(tmp_path, root=ROOT)
    assert report["status"] == "PASS"
    assert report["decision"] == "NO_IDENTITY_OVERLAP_DETECTED"
    assert report["downstream_gate"]["primary_surface_review_resolution"] == "IDENTITY_REVIEW_CLEAR"
    assert report["identity_resolution_truth"] is False


def test_unresolved_insufficient_fields_stays_review_required(tmp_path):
    write_json(tmp_path / "event_identity_resolution_gate_lite_v1.json", identity_payload(clusters=0, rows=0, unresolved=5))
    report = build_resolution(tmp_path, root=ROOT)
    assert report["status"] == "REVIEW_REQUIRED"
    assert report["decision"] == "UNRESOLVED_IDENTITY_INSUFFICIENT_FIELDS"
    assert report["downstream_gate"]["primary_surface_review_resolution"] == "WAIT"


def test_overlap_candidates_remain_review_required(tmp_path):
    write_json(tmp_path / "event_identity_resolution_gate_lite_v1.json", identity_payload(clusters=3, rows=8))
    report = build_resolution(tmp_path, root=ROOT)
    assert report["status"] == "REVIEW_REQUIRED"
    assert report["decision"] == "UNRESOLVED_IDENTITY_OVERLAP_REMAINS"
    assert "identity_overlap_candidates_present" in report["blocking_reasons"]
    assert report["review_candidate_count"] == 1


def test_duplicate_candidate_provenance_is_preserved(tmp_path):
    write_json(tmp_path / "event_identity_resolution_gate_lite_v1.json", identity_payload(clusters=1, rows=2))
    report = build_resolution(tmp_path, root=ROOT)
    assert report["review_candidates"][0]["provenance"][0]["source_row_index"] == 7


def test_source_support_conflict_keeps_unresolved(tmp_path):
    write_json(tmp_path / "event_identity_resolution_gate_lite_v1.json", identity_payload(clusters=0, rows=0))
    write_json(tmp_path / "source_conflict_registry_lite_v1.json", {"conflicts": [{"conflict_class": "NO_SUPPORTED_SURFACES", "severity": "FAIL_CLOSED", "evidence": {"source_count": 0}}]})
    report = build_resolution(tmp_path, root=ROOT)
    assert report["status"] == "REVIEW_REQUIRED"
    assert report["decision"] == "UNRESOLVED_SOURCE_SUPPORT_CONFLICTS_REMAIN"
    assert "source_support_blockers_present" in report["blocking_reasons"]


def test_no_deduplicated_event_count_claim(tmp_path):
    write_json(tmp_path / "event_identity_resolution_gate_lite_v1.json", identity_payload(clusters=2, rows=4))
    report = build_resolution(tmp_path, root=ROOT)
    assert report["canonical_event_count"] == "UNKNOWN"
    assert report["deduplicated_event_count"] == "UNKNOWN"
    assert report["identity_resolution_truth"] is False
    assert report["event_count_claim_allowed"] is False
    assert report["production_binding_allowed"] is False


def test_flat_phone_outputs(tmp_path):
    input_dir = tmp_path / "input"
    out = tmp_path / "HPFA"
    input_dir.mkdir()
    out.mkdir()
    write_json(input_dir / "event_identity_resolution_gate_lite_v1.json", identity_payload(clusters=1, rows=2))
    report = write_outputs(input_dir, out, root=ROOT)
    assert report["status"] == "REVIEW_REQUIRED"
    assert (out / "identity_review_resolution_lite_v1.json").exists()
    assert (out / "identity_review_resolution_lite_v1.txt").exists()
    assert not any(p.is_dir() for p in out.iterdir())


def test_nested_phone_output_directory_rejected(tmp_path):
    write_json(tmp_path / "event_identity_resolution_gate_lite_v1.json", identity_payload(clusters=1, rows=2))
    with pytest.raises(ValueError, match="nested_phone_output_directory_rejected"):
        write_outputs(tmp_path, "/sdcard/Download/HPFA/identity-review", root=ROOT)


def test_no_sample_match_identity_leak():
    src = (SRC / "identity_review_resolution.py").read_text(encoding="utf-8")
    contract = (ROOT / "docs" / "contracts" / "identity_review_resolution_lite_v1.md").read_text(encoding="utf-8")
    for token in ["Turkey", "Australia", "Türkiye", "Avustralya", "Juventus", "Galatasaray", "World Cup", "13.06.2026", "25.02.2026"]:
        assert token not in src
        assert token not in contract
