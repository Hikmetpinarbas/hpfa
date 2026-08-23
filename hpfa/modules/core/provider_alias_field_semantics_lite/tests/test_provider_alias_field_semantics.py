from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "provider_alias_field_semantics_lite" / "src"
sys.path.insert(0, str(SRC))

from provider_alias_field_semantics import build_semantics, norm, write_outputs


def csv_payload(status: str = "PASS") -> dict:
    columns = ["ID", "start", "end", "code", "team", "action", "half", "pos_x", "pos_y"]
    return {
        "module_id": "csv_surface_reader_lite_v1",
        "status": status,
        "canonical_event_count": "UNKNOWN",
        "hard_block_hits": [],
        "files": [{"relative_path": "events.csv", "source_role": "PLAYER_SURFACE_CANDIDATE", "column_profiles": [{"raw_column": c, "inferred_type": "string", "example_values": ["x"]} for c in columns]}],
    }


def xlsx_payload() -> dict:
    return {
        "module_id": "xlsx_surface_reader_lite_v1",
        "status": "PASS",
        "canonical_event_count": "UNKNOWN",
        "hard_block_hits": [],
        "files": [{"relative_path": "players.xlsx", "source_role": "PLAYER_SURFACE_CANDIDATE", "sheets": [{"source_role": "PLAYER_SURFACE_CANDIDATE", "column_profiles": [
            {"raw_column": "Player", "identity_role_candidate": "player", "inferred_type": "string"},
            {"raw_column": "Passes accurate, %", "identity_role_candidate": None, "percent_header_candidate": True, "inferred_type": "number"},
        ]}]}],
    }


def xml_payload() -> dict:
    fields = ["instance.ID", "instance.start", "instance.end", "instance.code", "instance.label.group", "instance.label.text"]
    return {
        "module_id": "xml_surface_reader_lite_v1",
        "status": "PASS",
        "canonical_event_count": "UNKNOWN",
        "hard_block_hits": [],
        "files": [{"relative_path": "events.xml", "source_role": "PLAYER_SURFACE_CANDIDATE", "field_inventory": [{"raw_field_path": f, "example_values": ["x"], "row_coverage_ratio": 1.0} for f in fields]}],
    }


def test_normalization_preserves_percent_semantics() -> None:
    assert norm("Passes accurate, %") == "passes_accurate_percent"


def test_exact_csv_and_xml_rules_map_to_shared_candidates() -> None:
    result = build_semantics(csv_payload(), xlsx_payload(), xml_payload())
    groups = {row["canonical_key_candidate"]: row for row in result["candidate_equivalence_groups"]}
    assert groups["event.start_time_candidate"]["cross_format_candidate"] is True
    assert groups["event.action_label_candidate"]["cross_format_candidate"] is True


def test_xlsx_metric_is_not_event_semantics() -> None:
    result = build_semantics(csv_payload(), xlsx_payload(), xml_payload())
    row = next(r for r in result["field_semantic_records"] if r["raw_field"] == "Passes accurate, %")
    assert row["semantic_family_candidate"] == "metric"
    assert row["canonical_key_candidate"] == "aggregate.metric_label_candidate"
    assert row["validated_semantics"] is False


def test_required_anchors_ready() -> None:
    result = build_semantics(csv_payload(), xlsx_payload(), xml_payload())
    assert result["required_anchor_audit"]["csv"]["ready_for_candidate_reconciliation"] is True
    assert result["required_anchor_audit"]["xml"]["ready_for_candidate_reconciliation"] is True


def test_unknown_field_is_preserved_not_guessed() -> None:
    payload = csv_payload()
    payload["files"][0]["column_profiles"].append({"raw_column": "vendor_blob"})
    result = build_semantics(payload, xlsx_payload(), xml_payload())
    row = next(r for r in result["field_semantic_records"] if r["raw_field"] == "vendor_blob")
    assert row["mapping_status"] == "UNKNOWN_PRESERVED"
    assert row["canonical_key_candidate"] is None


def test_upstream_fail_closed_blocks() -> None:
    result = build_semantics(csv_payload("FAIL_CLOSED"), xlsx_payload(), xml_payload())
    assert result["status"] == "FAIL_CLOSED"
    assert any(value.startswith("upstream_fail_closed") for value in result["hard_block_hits"])


def test_canonical_count_claim_blocks() -> None:
    payload = csv_payload()
    payload["canonical_event_count"] = 100
    result = build_semantics(payload, xlsx_payload(), xml_payload())
    assert result["status"] == "FAIL_CLOSED"
    assert any(value.startswith("canonical_event_count_claimed") for value in result["hard_block_hits"])


def test_active_match_execution_and_outputs(tmp_path: Path) -> None:
    root = tmp_path / "runtime" / "active_single_match" / "current"
    root.mkdir(parents=True)
    paths = []
    for name, payload in (("csv.json", csv_payload()), ("xlsx.json", xlsx_payload()), ("xml.json", xml_payload())):
        path = tmp_path / name
        path.write_text(json.dumps(payload), encoding="utf-8")
        paths.append(path)
    result = write_outputs(root, *paths, tmp_path / "HPFA")
    assert result["active_match_evidence_pass"] is True
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["production_release"] is False


def test_nested_phone_output_rejected(tmp_path: Path) -> None:
    root = tmp_path / "runtime" / "active_single_match" / "current"
    root.mkdir(parents=True)
    paths = []
    for name, payload in (("csv.json", csv_payload()), ("xlsx.json", xlsx_payload()), ("xml.json", xml_payload())):
        path = tmp_path / name
        path.write_text(json.dumps(payload), encoding="utf-8")
        paths.append(path)
    with pytest.raises(ValueError, match="nested_phone_output_directory_rejected"):
        write_outputs(root, *paths, tmp_path / "HPFA" / "nested")


def test_no_sample_match_identity_leak() -> None:
    source = (SRC / "provider_alias_field_semantics.py").read_text(encoding="utf-8")
    forbidden = ["Australia", "Turkey", "World Cup", "6935", "77798"]
    assert not any(token in source for token in forbidden)


def test_r08_temporal_order_guard_is_fail_closed() -> None:
    contract = json.loads(
        (
            ROOT
            / "hpfa/modules/core/provider_alias_field_semantics_lite/contract/provider_alias_field_semantics_lite_v1.json"
        ).read_text(encoding="utf-8")
    )
    guard = contract["temporal_order_guard"]
    boundary = contract["claim_boundary"]
    assert guard["time_field_candidate_is_football_order_truth"] is False
    assert guard["source_row_index_role"] == "PROVENANCE_ORDER_ONLY"
    assert guard["same_time_default_without_admitted_order_evidence"] == "SAME_TIME_UNORDERED"
    assert guard["event_type_priority_ordering_allowed"] is False
    assert guard["same_time_means_simultaneous_truth"] is False
    assert guard["downstream_order_sensitive_claim_decision"] == "REVIEW_REQUIRED"
    assert set(guard["allowed_relation_states"]) == {
        "BEFORE_CONFIRMED","AFTER_CONFIRMED","SAME_TIME_UNORDERED",
        "ORDER_INDETERMINATE","PROVENANCE_ORDER_ONLY",
    }
    assert boundary["validated_temporal_order"] is False
    assert boundary["source_row_order_truth"] is False
    assert boundary["sequence_truth"] is False
