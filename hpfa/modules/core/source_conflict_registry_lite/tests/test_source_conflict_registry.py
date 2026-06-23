import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "source_conflict_registry_lite" / "src"
sys.path.insert(0, str(SRC))

from source_conflict_registry import build_registry, write_outputs


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def mapping_payload():
    return {
        "module_id": "source_mapping_contract_lite_v1",
        "sources": [
            {"source_file": "Teams.csv", "source_role": "teams", "source_format": "csv", "source_surface_kind": "event_like_or_review", "rows_read": 100, "mapped_column_count": 3, "unmapped_column_count": 5, "missing_required_fields": [], "decision": "ACCEPT_MAPPING"},
            {"source_file": "Teams.xml", "source_role": "teams", "source_format": "xml", "source_surface_kind": "event_like_or_review", "rows_read": 101, "mapped_column_count": 0, "unmapped_column_count": 8, "missing_required_fields": ["event_type", "x", "y"], "decision": "DEGRADED_MISSING_REQUIRED"},
            {"source_file": "Players.xlsx", "source_role": "players", "source_format": "xlsx", "source_surface_kind": "aggregate_support", "rows_read": 30, "mapped_column_count": 2, "unmapped_column_count": 129, "missing_required_fields": [], "decision": "AGGREGATE_SUPPORT_MAPPING_ONLY"},
        ],
    }


def test_detect_unmapped_event_surface_conflict(tmp_path):
    write_json(tmp_path / "source_mapping_contract_v1.json", mapping_payload())

    registry = build_registry(tmp_path, root=ROOT)

    assert registry["status"] == "REVIEW_REQUIRED"
    assert registry["conflict_class_counts"]["UNMAPPED_EVENT_SURFACE"] == 1


def test_fail_closed_required_miss_still_creates_unmapped_event_conflict(tmp_path):
    payload = {
        "sources": [
            {"source_file": "Players.csv", "source_role": "players", "source_format": "csv", "source_surface_kind": "event_like_or_review", "rows_read": 7, "mapped_column_count": 1, "unmapped_column_count": 3, "missing_required_fields": ["event_type", "x", "y"], "decision": "FAIL_CLOSED_MISSING_REQUIRED"},
        ],
    }
    write_json(tmp_path / "source_mapping_contract_v1.json", payload)

    registry = build_registry(tmp_path, root=ROOT)

    assert registry["status"] == "REVIEW_REQUIRED"
    assert registry["conflict_class_counts"]["UNMAPPED_EVENT_SURFACE"] == 1
    assert registry["conflict_class_counts"]["REVIEW_REQUIRED_SOURCE"] == 1


def test_aggregate_support_not_event_required_conflict(tmp_path):
    write_json(tmp_path / "source_mapping_contract_v1.json", mapping_payload())

    registry = build_registry(tmp_path, root=ROOT)

    assert registry["conflict_class_counts"]["EVENT_LIKE_VS_AGGREGATE_SUPPORT"] == 1
    aggregate = [c for c in registry["conflicts"] if c["conflict_class"] == "EVENT_LIKE_VS_AGGREGATE_SUPPORT"][0]
    assert aggregate["severity"] == "INFO"


def test_row_count_discrepancy_by_role(tmp_path):
    write_json(tmp_path / "source_mapping_contract_v1.json", mapping_payload())

    registry = build_registry(tmp_path, root=ROOT)

    assert registry["conflict_class_counts"]["ROW_COUNT_DISCREPANCY_BY_ROLE"] == 1


def test_no_supported_surfaces_fail_closed(tmp_path):
    write_json(tmp_path / "source_mapping_contract_v1.json", {"sources": []})

    registry = build_registry(tmp_path, root=ROOT)

    assert registry["status"] == "FAIL_CLOSED"
    assert registry["conflict_class_counts"]["NO_SUPPORTED_SURFACES"] == 1


def test_primary_surface_unresolved_conflict(tmp_path):
    write_json(tmp_path / "source_mapping_contract_v1.json", {"sources": [{"source_file": "Teams.csv", "source_role": "teams", "source_format": "csv", "source_surface_kind": "event_like_or_review", "rows_read": 10, "mapped_column_count": 3, "unmapped_column_count": 0, "missing_required_fields": [], "decision": "ACCEPT_MAPPING"}]})
    write_json(tmp_path / "primary_event_surface_gate_lite_v1.json", {"status": "REVIEW_REQUIRED", "decision": "UNRESOLVED"})

    registry = build_registry(tmp_path, root=ROOT)

    assert registry["conflict_class_counts"]["PRIMARY_SURFACE_UNRESOLVED"] == 1


def test_metric_family_count_not_value_conflict(tmp_path):
    write_json(tmp_path / "source_mapping_contract_v1.json", {"sources": [{"source_file": "Teams.csv", "source_role": "teams", "source_format": "csv", "source_surface_kind": "event_like_or_review", "rows_read": 10, "mapped_column_count": 3, "unmapped_column_count": 0, "missing_required_fields": [], "decision": "ACCEPT_MAPPING"}]})
    write_json(tmp_path / "physical_cost_surface_audit_v1.json", {"record_count": 323, "family_counts": {"DISTANCE_TOTAL": 42}})

    registry = build_registry(tmp_path, root=ROOT)

    assert registry["conflict_class_counts"]["METRIC_FAMILY_COUNT_NOT_VALUE"] == 1


def test_flat_phone_outputs(tmp_path):
    input_dir = tmp_path / "input"
    out = tmp_path / "HPFA"
    input_dir.mkdir()
    out.mkdir()
    write_json(input_dir / "source_mapping_contract_v1.json", mapping_payload())

    registry = write_outputs(input_dir, out, root=ROOT)

    assert registry["status"] == "REVIEW_REQUIRED"
    assert (out / "source_conflict_registry_lite_v1.json").exists()
    assert (out / "source_conflict_registry_lite_v1.txt").exists()
    assert not any(p.is_dir() for p in out.iterdir())


def test_nested_phone_output_directory_rejected(tmp_path):
    write_json(tmp_path / "source_mapping_contract_v1.json", mapping_payload())

    with pytest.raises(ValueError, match="nested_phone_output_directory_rejected"):
        write_outputs(tmp_path, "/sdcard/Download/HPFA/source-conflict", root=ROOT)


def test_no_sample_match_identity_leak():
    src = (SRC / "source_conflict_registry.py").read_text(encoding="utf-8")
    contract = (ROOT / "docs" / "contracts" / "source_conflict_registry_lite_v1.md").read_text(encoding="utf-8")
    for token in ["Turkey", "Australia", "Türkiye", "Avustralya", "Juventus", "Galatasaray", "World Cup", "13.06.2026", "25.02.2026"]:
        assert token not in src
        assert token not in contract
