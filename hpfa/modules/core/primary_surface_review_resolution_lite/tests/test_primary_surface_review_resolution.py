import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "primary_surface_review_resolution_lite" / "src"
sys.path.insert(0, str(SRC))

from primary_surface_review_resolution import build_resolution, write_outputs


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def primary_payload(decision="UNRESOLVED_REVIEW_REQUIRED", reasons=None):
    return {
        "module_id": "primary_event_surface_gate_lite_v1",
        "decision": decision,
        "claim_safety": "PRIMARY_SURFACE_CANDIDATE_ONLY",
        "primary_event_surface_candidate": "UNRESOLVED" if decision != "CANDIDATE_SELECTED" else "Players.csv",
        "primary_event_surface_candidate_role": "UNRESOLVED" if decision != "CANDIDATE_SELECTED" else "players",
        "top_candidate_for_review": {
            "source_file": "Players.csv",
            "source_role": "players",
            "source_format": "csv",
            "candidate_score": 95.0,
        },
        "unresolved_reasons": reasons if reasons is not None else ["multiple_eligible_event_surfaces"],
        "canonical_event_count": "UNKNOWN",
        "deduplicated_event_count": "UNKNOWN",
        "event_count_claim_allowed": False,
    }


def source_conflict_payload(conflicts=None):
    return {
        "module_id": "source_conflict_registry_lite_v1",
        "claim_safety": "SOURCE_CONFLICT_EVIDENCE_ONLY",
        "conflicts": conflicts if conflicts is not None else [
            {"conflict_class": "SCHEMA_DIVERGENCE_BY_ROLE", "severity": "REVIEW_REQUIRED", "evidence": {"source_role": "players"}},
            {"conflict_class": "ROW_COUNT_DISCREPANCY_BY_ROLE", "severity": "REVIEW_REQUIRED", "evidence": {"source_role": "players"}},
            {"conflict_class": "EVENT_LIKE_VS_AGGREGATE_SUPPORT", "severity": "INFO", "evidence": {"source_file": "Players.xlsx"}},
            {"conflict_class": "PRIMARY_SURFACE_UNRESOLVED", "severity": "REVIEW_REQUIRED", "evidence": {"input_file": "primary_event_surface_gate_lite_v1.json"}},
        ],
    }


def test_missing_primary_gate_fail_closed(tmp_path):
    report = build_resolution(tmp_path, root=ROOT)

    assert report["status"] == "FAIL_CLOSED"
    assert report["decision"] == "FAIL_CLOSED_NO_PRIMARY_GATE"
    assert "no_primary_gate_output" in report["blocking_reasons"]


def test_no_review_candidate_fail_closed(tmp_path):
    write_json(tmp_path / "primary_event_surface_gate_lite_v1.json", {"decision": "UNRESOLVED_REVIEW_REQUIRED", "unresolved_reasons": ["no_eligible_event_surface"]})

    report = build_resolution(tmp_path, root=ROOT)

    assert report["status"] == "FAIL_CLOSED"
    assert report["decision"] == "FAIL_CLOSED_NO_REVIEW_CANDIDATE"


def test_already_selected_gate_is_preserved(tmp_path):
    write_json(tmp_path / "primary_event_surface_gate_lite_v1.json", primary_payload(decision="CANDIDATE_SELECTED", reasons=[]))

    report = build_resolution(tmp_path, root=ROOT)

    assert report["status"] == "PASS"
    assert report["decision"] == "ALREADY_CANDIDATE_SELECTED_BY_GATE"
    assert report["event_count_claim_allowed"] is False


def test_selected_gate_with_identity_overlap_stays_unresolved(tmp_path):
    write_json(tmp_path / "primary_event_surface_gate_lite_v1.json", primary_payload(decision="CANDIDATE_SELECTED", reasons=[]))
    write_json(tmp_path / "event_identity_resolution_gate_lite_v1.json", {"candidate_cluster_count": 1, "duplicate_risk_candidate_count": 2})

    report = build_resolution(tmp_path, root=ROOT)

    assert report["status"] == "REVIEW_REQUIRED"
    assert report["decision"] == "UNRESOLVED_IDENTITY_CONFLICTS_REMAIN"
    assert report["downstream_gate"]["time_phase_lite"] == "WAIT"


def test_selected_gate_with_selected_source_conflict_stays_unresolved(tmp_path):
    write_json(tmp_path / "primary_event_surface_gate_lite_v1.json", primary_payload(decision="CANDIDATE_SELECTED", reasons=[]))
    write_json(tmp_path / "source_conflict_registry_lite_v1.json", source_conflict_payload(conflicts=[
        {"conflict_class": "REVIEW_REQUIRED_SOURCE", "severity": "REVIEW_REQUIRED", "evidence": {"source_file": "Players.csv"}},
    ]))

    report = build_resolution(tmp_path, root=ROOT)

    assert report["status"] == "REVIEW_REQUIRED"
    assert report["decision"] == "UNRESOLVED_SOURCE_CONFLICTS_REMAIN"
    assert "top_candidate_has_source_conflict" in report["blocking_reasons"]


def test_unresolved_multiple_surface_can_resolve_to_review_candidate(tmp_path):
    write_json(tmp_path / "primary_event_surface_gate_lite_v1.json", primary_payload())
    write_json(tmp_path / "source_conflict_registry_lite_v1.json", source_conflict_payload())

    report = build_resolution(tmp_path, root=ROOT)

    assert report["status"] == "PASS"
    assert report["decision"] == "RESOLVED_CANDIDATE_FOR_DOWNSTREAM_REVIEW"
    assert report["review_candidate"]["source_file"] == "Players.csv"
    assert report["downstream_gate"]["time_phase_lite"] == "CANDIDATE_REVIEW_ONLY"
    assert report["canonical_event_count"] == "UNKNOWN"


def test_identity_overlap_keeps_unresolved(tmp_path):
    write_json(tmp_path / "primary_event_surface_gate_lite_v1.json", primary_payload(reasons=["overlap_candidates_present"]))
    write_json(tmp_path / "event_identity_resolution_gate_lite_v1.json", {"candidate_cluster_count": 2, "duplicate_risk_candidate_count": 5})

    report = build_resolution(tmp_path, root=ROOT)

    assert report["status"] == "REVIEW_REQUIRED"
    assert report["decision"] == "UNRESOLVED_IDENTITY_CONFLICTS_REMAIN"
    assert "identity_overlap_candidates_present" in report["blocking_reasons"]


def test_top_candidate_source_conflict_keeps_unresolved(tmp_path):
    write_json(tmp_path / "primary_event_surface_gate_lite_v1.json", primary_payload())
    write_json(tmp_path / "source_conflict_registry_lite_v1.json", source_conflict_payload(conflicts=[
        {"conflict_class": "UNMAPPED_EVENT_SURFACE", "severity": "REVIEW_REQUIRED", "evidence": {"source_file": "Players.csv"}},
    ]))

    report = build_resolution(tmp_path, root=ROOT)

    assert report["status"] == "REVIEW_REQUIRED"
    assert report["decision"] == "UNRESOLVED_SOURCE_CONFLICTS_REMAIN"
    assert "top_candidate_has_source_conflict" in report["blocking_reasons"]


def test_flat_phone_outputs(tmp_path):
    input_dir = tmp_path / "input"
    out = tmp_path / "HPFA"
    input_dir.mkdir()
    out.mkdir()
    write_json(input_dir / "primary_event_surface_gate_lite_v1.json", primary_payload())

    report = write_outputs(input_dir, out, root=ROOT)

    assert report["status"] == "PASS"
    assert (out / "primary_surface_review_resolution_lite_v1.json").exists()
    assert (out / "primary_surface_review_resolution_lite_v1.txt").exists()
    assert not any(p.is_dir() for p in out.iterdir())


def test_nested_phone_output_directory_rejected(tmp_path):
    write_json(tmp_path / "primary_event_surface_gate_lite_v1.json", primary_payload())

    with pytest.raises(ValueError, match="nested_phone_output_directory_rejected"):
        write_outputs(tmp_path, "/sdcard/Download/HPFA/primary-resolution", root=ROOT)


def test_no_sample_match_identity_leak():
    src = (SRC / "primary_surface_review_resolution.py").read_text(encoding="utf-8")
    contract = (ROOT / "docs" / "contracts" / "primary_surface_review_resolution_lite_v1.md").read_text(encoding="utf-8")
    for token in ["Turkey", "Australia", "Türkiye", "Avustralya", "Juventus", "Galatasaray", "World Cup", "13.06.2026", "25.02.2026"]:
        assert token not in src
        assert token not in contract
