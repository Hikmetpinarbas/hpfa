import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "canonical_mapping_report_lite" / "src"
sys.path.insert(0, str(SRC))

from canonical_mapping_report import build_report


def field_surface():
    return {
        "field_semantic_records": [
            {"source_column": "event_type", "normalized_column": "event_type", "semantic_family": "action"},
            {"source_column": "minute", "normalized_column": "minute", "semantic_family": "time"},
            {"source_column": "vendor_blob", "normalized_column": "vendor_blob", "semantic_family": "unknown"},
        ]
    }


def registry():
    return {
        "records": [
            {"normalized_alias": "event_type", "canonical_key_candidate": "event.action", "rule_id": "r1", "alias_reliability": "MEDIUM"},
            {"normalized_alias": "minute", "canonical_key_candidate": "event.minute", "rule_id": "r2", "alias_reliability": "MEDIUM"},
        ]
    }


def test_canonical_mapping_report_written():
    report = build_report(field_surface(), registry())
    assert report["module_id"] == "canonical_mapping_report_lite_v1"
    assert report["mapping_records"]


def test_mapping_report_keeps_unmapped_fields():
    report = build_report(field_surface(), registry())
    assert report["unmapped_preserved_count"] == 1
    assert report["preserved_unmapped_fields"][0]["normalized_column"] == "vendor_blob"


def test_no_canonical_event_count_claim():
    report = build_report(field_surface(), registry())
    assert report["surface_inventory"]["canonical_event_count"] == "UNKNOWN"


def test_missing_required_detection():
    report = build_report(field_surface(), registry())
    assert "event.team" in report["missing_required_fields"]
    assert report["status"] == "REVIEW_REQUIRED"


def test_alias_candidate_not_runtime_truth():
    report = build_report(field_surface(), registry())
    first = report["mapping_records"][0]
    assert first["mapping_status"] == "CANDIDATE_HIT"
    assert first["runtime_verified"] is False


def test_no_sample_match_identity_leak():
    src = (SRC / "canonical_mapping_report.py").read_text(encoding="utf-8")
    for token in ["Turkey", "Australia", "United States", "World Cup", "25.06.2026"]:
        assert token not in src
