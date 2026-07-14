from __future__ import annotations

import json
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from event_instance_admission_guard import build_report, write_outputs


def _row(source_file: str, row_index: int, *, label: str = "Successful pass", fmt: str = "csv", player: str | None = "Player 1") -> dict:
    row = {
        "source_file": source_file,
        "source_format": fmt,
        "source_role": "players",
        "source_row_index": row_index,
        "row_surface_class": "EVENT_LIKE_SOURCE_CANDIDATE",
        "source_event_id_raw": str(row_index),
        "start_raw": str(100 + row_index),
        "period_candidate": "FIRST_HALF",
        "team_raw": "TEAM_A",
        "event_type_raw": label,
        "event_family": "PASS",
        "x_meters": 10.0,
        "y_meters": 20.0,
    }
    if player is not None:
        row["player_raw"] = player
    return row


def _manifest(*entries: dict) -> dict:
    return {"sources": list(entries)}


def _entry(
    source_file: str,
    *,
    source_file_id: str,
    role: str,
    allowed: bool,
    content_hash: str,
    target_status: str = "TARGET_MATCH_CONFIRMED",
    match_binding_id: str = "active_single_match_current",
) -> dict:
    return {
        "source_file_id": source_file_id,
        "source_file": source_file,
        "provider": "sportsbase",
        "source_role": role,
        "match_binding_id": match_binding_id,
        "target_match_status": target_status,
        "event_generation_allowed": allowed,
        "source_content_hash": content_hash,
    }


def _write(tmp_path: Path, rows: list[dict], manifest: dict) -> tuple[Path, Path]:
    canonical = tmp_path / "canonical.json"
    source_manifest = tmp_path / "manifest.json"
    canonical.write_text(json.dumps({"rows": rows}), encoding="utf-8")
    source_manifest.write_text(json.dumps(manifest), encoding="utf-8")
    return canonical, source_manifest


def _primary(source_file: str = "Players.csv", content_hash: str = "hash-primary") -> dict:
    return _entry(
        source_file,
        source_file_id="csv_primary_01",
        role="CSV_PRIMARY_CANONICAL_ACTION_SURFACE",
        allowed=True,
        content_hash=content_hash,
    )


def test_event_label_registry_does_not_create_events(tmp_path):
    canonical, manifest = _write(tmp_path, [_row("Players.csv", 1)], _manifest(_primary()))
    report = build_report(canonical, manifest)
    assert report["label_registry_count"] == 1
    assert report["admitted_event_candidate_count"] == 1
    assert report["label_registry"][0]["event_generation_allowed"] is False


def test_only_primary_action_surface_can_generate_event_candidates(tmp_path):
    rows = [_row("Players.csv", 1), _row("Players.xml", 1, fmt="xml")]
    manifest = _manifest(
        _primary(),
        _entry("Players.xml", source_file_id="xml_01", role="XML_CONFORMANCE_SURFACE", allowed=False, content_hash="hash-xml"),
    )
    canonical, manifest_path = _write(tmp_path, rows, manifest)
    report = build_report(canonical, manifest_path)
    assert report["admitted_event_candidate_count"] == 1
    assert report["support_only_row_count"] == 1


def test_xml_surface_is_support_only(tmp_path):
    rows = [_row("Players.csv", 1), _row("Players.xml", 1, fmt="xml")]
    manifest = _manifest(
        _primary(),
        _entry("Players.xml", source_file_id="xml_01", role="XML_QUALIFIER_SUPPORT_SURFACE", allowed=False, content_hash="hash-xml"),
    )
    canonical, manifest_path = _write(tmp_path, rows, manifest)
    report = build_report(canonical, manifest_path)
    assert all(item["source_file"] != "Players.xml" for item in report["event_instance_candidates"])


def test_xlsx_aggregate_surface_is_support_only(tmp_path):
    rows = [_row("Players.csv", 1), _row("Players.xlsx", 1, fmt="xlsx")]
    manifest = _manifest(
        _primary(),
        _entry("Players.xlsx", source_file_id="xlsx_01", role="XLSX_AGGREGATE_VALIDATION_SURFACE", allowed=False, content_hash="hash-xlsx"),
    )
    canonical, manifest_path = _write(tmp_path, rows, manifest)
    report = build_report(canonical, manifest_path)
    assert report["admitted_event_candidate_count"] == 1
    assert report["support_only_row_count"] == 1


def test_derived_runtime_output_cannot_reenter_raw_pool(tmp_path):
    rows = [_row("derived.json", 1)]
    manifest = _manifest(
        _entry("derived.json", source_file_id="derived_01", role="DERIVED_RUNTIME_OUTPUT", allowed=True, content_hash="hash-derived")
    )
    canonical, manifest_path = _write(tmp_path, rows, manifest)
    report = build_report(canonical, manifest_path)
    assert report["decision_state"] == "BLOCK_DERIVED_RAW_REINGESTION"
    assert report["admitted_event_candidate_count"] == 0


def test_duplicate_file_hash_blocks_source_inflation(tmp_path):
    rows = [_row("Players.csv", 1), _row("Copy.csv", 1)]
    manifest = _manifest(
        _primary(content_hash="same-hash"),
        _entry("Copy.csv", source_file_id="copy_01", role="CSV_SECONDARY_SUPPORT_SURFACE", allowed=False, content_hash="same-hash"),
    )
    canonical, manifest_path = _write(tmp_path, rows, manifest)
    report = build_report(canonical, manifest_path)
    assert report["decision_state"] == "BLOCK_DUPLICATE_SOURCE"
    assert report["admitted_event_candidate_count"] == 0


def test_same_upstream_not_counted_as_independent_support(tmp_path):
    rows = [_row("Players.csv", 1), _row("Copy.xml", 1, fmt="xml")]
    manifest = _manifest(
        _primary(content_hash="same-upstream"),
        _entry("Copy.xml", source_file_id="xml_01", role="XML_CONFORMANCE_SURFACE", allowed=False, content_hash="same-upstream"),
    )
    canonical, manifest_path = _write(tmp_path, rows, manifest)
    report = build_report(canonical, manifest_path)
    assert "duplicate_source_hash" in report["manifest_failures"]


def test_event_candidate_requires_source_file_id(tmp_path):
    bad = _primary()
    bad["source_file_id"] = ""
    canonical, manifest = _write(tmp_path, [_row("Players.csv", 1)], _manifest(bad))
    report = build_report(canonical, manifest)
    assert report["admitted_event_candidate_count"] == 0


def test_event_candidate_requires_source_row_index(tmp_path):
    row = _row("Players.csv", 1)
    row["source_row_index"] = None
    canonical, manifest = _write(tmp_path, [row], _manifest(_primary()))
    report = build_report(canonical, manifest)
    assert report["quarantined_row_count"] == 1


def test_event_candidate_requires_match_binding(tmp_path):
    bad = _primary()
    bad["match_binding_id"] = ""
    canonical, manifest = _write(tmp_path, [_row("Players.csv", 1)], _manifest(bad))
    report = build_report(canonical, manifest)
    assert report["admitted_event_candidate_count"] == 0


def test_non_target_match_is_quarantined(tmp_path):
    bad = _primary()
    bad["target_match_status"] = "NON_TARGET_MATCH"
    canonical, manifest = _write(tmp_path, [_row("Players.csv", 1)], _manifest(bad))
    report = build_report(canonical, manifest)
    assert report["decision_state"] == "BLOCK_NON_TARGET_MATCH"


def test_raw_label_is_preserved(tmp_path):
    canonical, manifest = _write(tmp_path, [_row("Players.csv", 1, label="Successful Pass")], _manifest(_primary()))
    report = build_report(canonical, manifest)
    assert report["event_instance_candidates"][0]["raw_event_label"] == "Successful Pass"


def test_normalized_label_is_stored_separately(tmp_path):
    canonical, manifest = _write(tmp_path, [_row("Players.csv", 1, label=" Successful-Pass ")], _manifest(_primary()))
    report = build_report(canonical, manifest)
    event = report["event_instance_candidates"][0]
    assert event["raw_event_label"] == "Successful-Pass"
    assert event["normalized_event_label"] == "successful_pass"


def test_unknown_label_is_audit_only(tmp_path):
    row = _row("Players.csv", 1, label="Mystery action")
    row["event_family"] = "UNKNOWN_OR_OTHER"
    canonical, manifest = _write(tmp_path, [row], _manifest(_primary()))
    report = build_report(canonical, manifest)
    assert report["label_registry"][0]["audit_status"] == "AUDIT_ONLY"
    assert report["admitted_event_candidate_count"] == 0
    assert report["unknown_label_audit_only_count"] == 1


def test_support_surface_does_not_create_duplicate_candidate(tmp_path):
    rows = [_row("Players.csv", 1), _row("Players.xml", 1, fmt="xml")]
    manifest = _manifest(
        _primary(),
        _entry("Players.xml", source_file_id="xml_01", role="XML_CONFORMANCE_SURFACE", allowed=False, content_hash="hash-xml"),
    )
    canonical, manifest_path = _write(tmp_path, rows, manifest)
    report = build_report(canonical, manifest_path)
    assert len(report["event_instance_candidates"]) == 1


def test_row_fingerprint_collision_requires_review(tmp_path):
    rows = [_row("Players.csv", 1), _row("Players.csv", 2)]
    rows[1]["source_event_id_raw"] = rows[0]["source_event_id_raw"]
    rows[1]["start_raw"] = rows[0]["start_raw"]
    canonical, manifest = _write(tmp_path, rows, _manifest(_primary()))
    report = build_report(canonical, manifest)
    assert report["duplicate_row_candidates"][0]["decision"] == "POSSIBLE_COLLISION_REVIEW_REQUIRED"
    assert report["decision_state"] == "REVIEW_REQUIRED_PRIMARY_SURFACE_NOT_ATOMIC"
    assert report["admitted_event_candidate_count"] == 0
    assert report["provisional_event_candidate_count"] == 2


def test_player_primary_without_player_binding_requires_review(tmp_path):
    canonical, manifest = _write(tmp_path, [_row("Players.csv", 1, player=None)], _manifest(_primary()))
    report = build_report(canonical, manifest)
    assert report["primary_identity_missing_player_count"] == 1
    assert report["decision_state"] == "REVIEW_REQUIRED_PRIMARY_SURFACE_NOT_ATOMIC"
    assert report["admitted_event_candidate_count"] == 0


def test_boundary_marker_is_support_not_event(tmp_path):
    row = _row("Players.csv", 1, label="Start of the 1st half")
    canonical, manifest = _write(tmp_path, [row], _manifest(_primary()))
    report = build_report(canonical, manifest)
    assert report["admitted_event_candidate_count"] == 0
    assert report["support_surface_records"][0]["support_type"] == "MATCH_BOUNDARY_MARKER"


def test_multiple_event_generators_block(tmp_path):
    rows = [_row("Players.csv", 1), _row("Teams.csv", 1)]
    manifest = _manifest(
        _primary(),
        _entry("Teams.csv", source_file_id="csv_primary_02", role="CSV_PRIMARY_CANONICAL_ACTION_SURFACE", allowed=True, content_hash="hash-two"),
    )
    canonical, manifest_path = _write(tmp_path, rows, manifest)
    report = build_report(canonical, manifest_path)
    assert report["decision_state"] == "BLOCK_MULTIPLE_EVENT_GENERATORS"


def test_canonical_event_count_remains_unknown(tmp_path):
    canonical, manifest = _write(tmp_path, [_row("Players.csv", 1)], _manifest(_primary()))
    report = build_report(canonical, manifest)
    assert report["canonical_event_count"] == "UNKNOWN"


def test_flat_phone_outputs(tmp_path):
    canonical, manifest = _write(tmp_path, [_row("Players.csv", 1)], _manifest(_primary()))
    out = tmp_path / "Download" / "HPFA"
    report = write_outputs(canonical, manifest, out)
    assert report["decision_state"] == "PASS_EVENT_INSTANCE_ADMISSION"
    assert (out / "event_instance_admission_guard_lite_v1.json").exists()


def test_nested_phone_output_directory_rejected(tmp_path):
    canonical, manifest = _write(tmp_path, [_row("Players.csv", 1)], _manifest(_primary()))
    nested = tmp_path / "Download" / "HPFA" / "nested"
    try:
        write_outputs(canonical, manifest, nested)
    except ValueError as exc:
        assert str(exc) == "nested_phone_output_directory_rejected"
    else:
        raise AssertionError("nested path must be rejected")
