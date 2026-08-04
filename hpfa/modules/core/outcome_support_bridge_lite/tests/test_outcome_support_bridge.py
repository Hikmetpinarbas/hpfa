from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src" / "outcome_support_bridge.py"
spec = importlib.util.spec_from_file_location("outcome_support_bridge", SRC)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


def payloads(*, terminal=False, derived=False, visible="NEUTRAL_VISIBLE_CONSEQUENCE_CANDIDATE", sequence=False):
    binding = "msb_test"
    node = {
        "selected_action_node_id": "node_1",
        "match_surface_binding_id": binding,
        "team_identity_candidate_id": "team_1",
        "actor_identity_candidate_id": "actor_1",
        "source_role": "PLAYER_SURFACE_CANDIDATE",
        "period_candidate": "1",
        "action_family_candidates": ["PASS"],
        "supporting_evidence_atom_ids": ["atom_1"] if terminal or derived else [],
        "terminal_outcome_support_visible": terminal,
        "derived_consequence_support_visible": derived,
    }
    selected_action = {
        "module_id": "selected_action_consequence_surface_lite_v1",
        "status": "REVIEW_REQUIRED",
        "module_status": "REVIEW_REQUIRED",
        "match_surface_binding_id": binding,
        "selected_action_nodes": [node],
        "selected_action_node_count": 1,
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }
    event = {
        "selected_event_consequence_candidate_id": "event_1",
        "anchor_selected_action_node_id": "node_1",
        "match_surface_binding_id": binding,
        "team_identity_candidate_id": "team_1",
        "actor_identity_candidate_id": "actor_1",
        "source_role": "PLAYER_SURFACE_CANDIDATE",
        "period_candidate": "1",
        "consequence_class_candidate": visible,
        "zone_delta_class": "NO_ZONE_CHANGE_CANDIDATE",
        "turnover_window_class": "NOT_APPLICABLE",
        "retention_after_action_status": "VISIBLE_RETENTION_CANDIDATE_TRUE",
    }
    selected_event = {
        "module_id": "selected_event_consequence_surface_lite_v1",
        "status": "REVIEW_REQUIRED",
        "module_status": "REVIEW_REQUIRED",
        "match_surface_binding_id": binding,
        "selected_event_consequence_candidates": [event],
        "selected_event_consequence_candidate_count": 1,
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }
    metric = {
        "metric_record_id": "metric_1",
        "metric_id": "sequence_survival_rate",
        "status": "PASS_CANDIDATE",
        "claim_ceiling": "candidate_sequence_continuation",
        "evidence_anchor_node_ids": ["node_1"] if sequence else [],
    }
    sequence_payload = {
        "module_id": "eventonly_sequence_consequence_engine_lite_v1",
        "status": "REVIEW_REQUIRED",
        "module_status": "REVIEW_REQUIRED",
        "match_surface_binding_id": binding,
        "metric_records": [metric],
        "metric_record_count": 1,
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }
    return selected_action, selected_event, sequence_payload


def build(**kwargs):
    return module.build_outcome_support_bridge(*payloads(**kwargs))


def test_explicit_terminal_support_is_admitted():
    result = build(terminal=True, visible="UNRESOLVED_VISIBLE_CONSEQUENCE_REVIEW_REQUIRED")
    record = result["outcome_support_bridge_records"][0]
    assert record["outcome_support_classification"] == "EXPLICIT_TERMINAL_OUTCOME_SUPPORT"
    assert record["downstream_promotion_allowed"] is True
    assert record["terminal_outcome_truth"] is False


def test_explicit_derived_support_is_admitted():
    result = build(derived=True, visible="UNRESOLVED_VISIBLE_CONSEQUENCE_REVIEW_REQUIRED")
    record = result["outcome_support_bridge_records"][0]
    assert record["outcome_support_classification"] == "EXPLICIT_DERIVED_CONSEQUENCE_SUPPORT"


def test_visible_consequence_support_is_separate_from_terminal_truth():
    result = build()
    record = result["outcome_support_bridge_records"][0]
    assert record["outcome_support_classification"] == "VISIBLE_CONSEQUENCE_SUPPORT_ONLY"
    assert record["downstream_outcome_support_status"] == "SUPPORTED_CANDIDATE"
    assert record["terminal_outcome_truth"] is False


def test_sequence_support_alone_cannot_promote():
    result = build(visible="UNRESOLVED_VISIBLE_CONSEQUENCE_REVIEW_REQUIRED", sequence=True)
    record = result["outcome_support_bridge_records"][0]
    assert record["outcome_support_classification"] == "SEQUENCE_TRACE_SUPPORT_ONLY"
    assert record["downstream_outcome_support_status"] == "SUPPORT_ONLY"
    assert record["downstream_promotion_allowed"] is False
    assert record["sequence_trace_truth"] is False


def test_multiple_compatible_sources_are_disclosed():
    result = build(terminal=True, sequence=True)
    record = result["outcome_support_bridge_records"][0]
    assert record["outcome_support_classification"] == "MULTI_SOURCE_COMPATIBLE_OUTCOME_SUPPORT"
    assert len(record["support_sources"]) == 3


def test_unresolved_without_support_remains_unavailable():
    result = build(visible="UNRESOLVED_VISIBLE_CONSEQUENCE_REVIEW_REQUIRED")
    record = result["outcome_support_bridge_records"][0]
    assert record["outcome_support_classification"] == "OUTCOME_SUPPORT_UNAVAILABLE"
    assert record["downstream_promotion_allowed"] is False


def test_cross_period_lineage_is_conflicted_not_promoted():
    selected_action, selected_event, sequence = payloads()
    selected_event["selected_event_consequence_candidates"][0]["period_candidate"] = "2"
    result = module.build_outcome_support_bridge(selected_action, selected_event, sequence)
    record = result["outcome_support_bridge_records"][0]
    assert record["outcome_support_classification"] == "CONFLICTED_OUTCOME_SUPPORT"
    assert "period_candidate_mismatch" in record["conflict_reasons"]
    assert record["downstream_promotion_allowed"] is False


def test_missing_selected_event_coverage_fails_closed():
    selected_action, selected_event, sequence = payloads()
    selected_event["selected_event_consequence_candidates"] = []
    selected_event["selected_event_consequence_candidate_count"] = 0
    result = module.build_outcome_support_bridge(selected_action, selected_event, sequence)
    assert result["status"] == "FAIL_CLOSED"
    assert any(hit.startswith("selected_event_coverage_missing") for hit in result["hard_block_hits"])


def test_sequence_anchor_reference_must_exist():
    selected_action, selected_event, sequence = payloads(sequence=True)
    sequence["metric_records"][0]["evidence_anchor_node_ids"] = ["missing"]
    result = module.build_outcome_support_bridge(selected_action, selected_event, sequence)
    assert result["status"] == "FAIL_CLOSED"
    assert any(hit.startswith("sequence_metric_anchor_reference_missing") for hit in result["hard_block_hits"])


def test_explicit_support_requires_atom_lineage():
    selected_action, selected_event, sequence = payloads(terminal=True)
    selected_action["selected_action_nodes"][0]["supporting_evidence_atom_ids"] = []
    result = module.build_outcome_support_bridge(selected_action, selected_event, sequence)
    record = result["outcome_support_bridge_records"][0]
    assert record["outcome_support_classification"] == "CONFLICTED_OUTCOME_SUPPORT"
    assert "explicit_support_flag_without_evidence_atom_lineage" in record["conflict_reasons"]


def test_nested_phone_output_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="nested_phone_output_directory_rejected"):
        module.validate_out(tmp_path / "HPFA" / "nested")


def test_no_metric_rate_output():
    result = build()
    assert result["metric_rate_output_allowed"] is False
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["production_release"] is False
