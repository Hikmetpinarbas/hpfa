import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "minimum_viable_context_lite" / "src"
sys.path.insert(0, str(SRC))

from minimum_viable_context import build_context_candidates, resolve_time_evidence
from semantic_context_adapter import adapt_rows, build_column_map


def field_surface():
    return {
        "field_semantic_records": [
            {"source_column": "event_type", "normalized_column": "event_type", "semantic_family": "action"},
            {"source_column": "team_id", "normalized_column": "team_id", "semantic_family": "actor"},
            {"source_column": "minute", "normalized_column": "minute", "semantic_family": "time"},
            {"source_column": "x", "normalized_column": "x", "semantic_family": "space"},
            {"source_column": "y", "normalized_column": "y", "semantic_family": "space"},
        ]
    }


def mapping_report():
    return {
        "mapping_records": [
            {"source_column": "event_type", "canonical_key_candidate": "event.action"},
            {"source_column": "team_id", "canonical_key_candidate": "event.team"},
            {"source_column": "minute", "canonical_key_candidate": "event.minute"},
            {"source_column": "x", "canonical_key_candidate": "event.start_x"},
            {"source_column": "y", "canonical_key_candidate": "event.start_y"},
        ]
    }


def test_semantic_field_records_map_to_context_keys():
    colmap = build_column_map(field_surface(), mapping_report())
    assert colmap["event_type"] == "event_type"
    assert colmap["team_id"] == "team"
    assert colmap["minute"] == "minute"
    assert colmap["x"] == "x"
    assert colmap["y"] == "y"


def test_semantic_rows_feed_minimum_viable_context_candidates():
    rows = [{"event_type": "pass", "team_id": "A", "minute": "12", "x": "72", "y": "34"}]
    adapted = adapt_rows(rows, field_surface(), mapping_report())
    candidates = build_context_candidates(adapted["rows"])
    assert candidates[0]["action_family"] == "PASS"
    assert candidates[0]["team_label"] == "a"
    assert candidates[0]["zone_candidate"] == "FINAL_THIRD"
    assert candidates[0]["channel_candidate"] == "CENTRAL_CHANNEL"


def test_absolute_time_seconds_survives_adapter_as_absolute_second():
    surface = {
        "field_semantic_records": [
            {"source_column": "absolute_time_seconds", "normalized_column": "absolute_time_seconds", "semantic_family": "time"},
        ]
    }
    report = {
        "mapping_records": [
            {"source_column": "absolute_time_seconds", "canonical_key_candidate": "event.second"},
        ]
    }
    adapted = adapt_rows([{"absolute_time_seconds": "995"}], surface, report)
    row = adapted["rows"][0]
    assert row["absolute_time_seconds"] == "995"
    assert "second" not in row
    evidence = resolve_time_evidence(row)
    assert evidence["time_admission_status"] == "ADMITTED"
    assert evidence["time_unit_status"] == "SECOND"
    assert evidence["football_minute_candidate"] == 16
    assert not any(
        item.get("reason") == "IMPLAUSIBLE_COMPONENT_SECOND_RANGE"
        for item in evidence["rejected_time_field_candidates"]
    )


def test_match_second_survives_adapter_as_absolute_second():
    surface = {
        "field_semantic_records": [
            {"source_column": "match_second", "normalized_column": "match_second", "semantic_family": "time"},
        ]
    }
    adapted = adapt_rows([{"match_second": "995"}], surface)
    row = adapted["rows"][0]
    assert row["match_second"] == "995"
    assert "second" not in row
    evidence = resolve_time_evidence(row)
    assert evidence["time_admission_status"] == "ADMITTED"
    assert evidence["time_unit_status"] == "SECOND"
    assert evidence["football_minute_candidate"] == 16


def test_generic_second_remains_component_second_not_absolute():
    surface = {
        "field_semantic_records": [
            {"source_column": "second", "normalized_column": "second", "semantic_family": "time"},
        ]
    }
    adapted = adapt_rows([{"second": "34"}], surface)
    row = adapted["rows"][0]
    assert row["second"] == "34"
    evidence = resolve_time_evidence(row)
    assert evidence["time_admission_status"] == "REVIEW_REQUIRED_UNKNOWN_TIME_UNIT"
    assert evidence["football_minute_candidate"] is None
    assert any(
        item.get("reason") == "COMPONENT_SECOND_RELATION_NOT_ADMITTED"
        for item in evidence["rejected_time_field_candidates"]
    )


def test_unmapped_columns_are_preserved_not_guessed():
    rows = [{"danger_blob": "1", "event_type": "shot"}]
    adapted = adapt_rows(rows, field_surface(), mapping_report())
    assert "danger_blob" in adapted["unmapped_columns"]
    assert adapted["rows"][0]["_preserved_unmapped"]["danger_blob"] == "1"
    assert adapted["status"] == "REVIEW_REQUIRED"


def test_adapter_does_not_create_event_truth():
    adapted = adapt_rows([{"event_type": "pass"}], field_surface(), mapping_report())
    assert adapted["canonical_event_count"] == "UNKNOWN"
    assert adapted["runtime_verified"] is False
    assert adapted["claim_boundary"] == "semantic_context_adapter_candidate_only"


def test_no_sample_match_identity_leak():
    src = (SRC / "semantic_context_adapter.py").read_text(encoding="utf-8")
    for token in ["Turkey", "Australia", "United States", "World Cup", "25.06.2026"]:
        assert token not in src