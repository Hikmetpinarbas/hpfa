from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src" / "outcome_support_bridge.py"
spec = importlib.util.spec_from_file_location("outcome_support_bridge", SRC)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


def payloads(
    *,
    terminal: bool = False,
    derived: bool = False,
    visible: str = "NEUTRAL_VISIBLE_CONSEQUENCE_CANDIDATE",
    sequence: bool = False,
):
    binding = "msb_test"
    atom_ids: list[object] = []
    atom_counts: dict[str, int] = {}
    if terminal:
        atom_ids.append("atom_terminal")
        atom_counts["TERMINAL_OUTCOME_ATOM"] = 1
    if derived:
        atom_ids.append("atom_derived")
        atom_counts["DERIVED_CONSEQUENCE_ATOM"] = 1

    node = {
        "selected_action_node_id": "node_1",
        "match_surface_binding_id": binding,
        "team_identity_candidate_id": "team_1",
        "actor_identity_candidate_id": "actor_1",
        "source_role": "PLAYER_SURFACE_CANDIDATE",
        "period_candidate": "1",
        "action_family_candidates": ["PASS"],
        "supporting_evidence_atom_ids": atom_ids,
        "support_atom_class_counts": atom_counts,
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


def record(result):
    return result["outcome_support_bridge_records"][0]


def test_explicit_terminal_support_is_admitted():
    result = build(terminal=True, visible="UNRESOLVED_VISIBLE_CONSEQUENCE_REVIEW_REQUIRED")
    row = record(result)
    assert row["outcome_support_classification"] == "EXPLICIT_TERMINAL_OUTCOME_SUPPORT"
    assert row["downstream_promotion_allowed"] is True
    assert row["terminal_outcome_truth"] is False


def test_explicit_derived_support_is_admitted():
    row = record(build(derived=True, visible="UNRESOLVED_VISIBLE_CONSEQUENCE_REVIEW_REQUIRED"))
    assert row["outcome_support_classification"] == "EXPLICIT_DERIVED_CONSEQUENCE_SUPPORT"


def test_visible_consequence_support_is_separate_from_terminal_truth():
    row = record(build())
    assert row["outcome_support_classification"] == "VISIBLE_CONSEQUENCE_SUPPORT_ONLY"
    assert row["downstream_outcome_support_status"] == "SUPPORTED_CANDIDATE"
    assert row["terminal_outcome_truth"] is False


def test_sequence_support_alone_cannot_promote():
    result = build(visible="UNRESOLVED_VISIBLE_CONSEQUENCE_REVIEW_REQUIRED", sequence=True)
    row = record(result)
    assert result["payload_binding_gate_pass"] is True
    assert result["module_hard_block_gate_pass"] is True
    assert row["outcome_support_classification"] == "SEQUENCE_TRACE_SUPPORT_ONLY"
    assert row["downstream_outcome_support_status"] == "SUPPORT_ONLY"
    assert row["downstream_promotion_allowed"] is False
    assert row["sequence_trace_truth"] is False


def test_multiple_compatible_sources_are_disclosed():
    row = record(build(terminal=True, sequence=True))
    assert row["outcome_support_classification"] == "MULTI_SOURCE_COMPATIBLE_OUTCOME_SUPPORT"
    assert len(row["support_sources"]) == 3


def test_unresolved_without_support_remains_unavailable():
    row = record(build(visible="UNRESOLVED_VISIBLE_CONSEQUENCE_REVIEW_REQUIRED"))
    assert row["outcome_support_classification"] == "OUTCOME_SUPPORT_UNAVAILABLE"
    assert row["downstream_promotion_allowed"] is False


def test_cross_period_lineage_is_conflicted_not_promoted():
    selected_action, selected_event, sequence = payloads()
    selected_event["selected_event_consequence_candidates"][0]["period_candidate"] = "2"
    row = record(module.build_outcome_support_bridge(selected_action, selected_event, sequence))
    assert row["outcome_support_classification"] == "CONFLICTED_OUTCOME_SUPPORT"
    assert "period_candidate_mismatch" in row["conflict_reasons"]
    assert row["downstream_promotion_allowed"] is False


def test_missing_record_binding_cannot_use_payload_fallback():
    selected_action, selected_event, sequence = payloads()
    del selected_action["selected_action_nodes"][0]["match_surface_binding_id"]
    row = record(module.build_outcome_support_bridge(selected_action, selected_event, sequence))
    assert "match_surface_binding_id_missing_on_selected_action" in row["conflict_reasons"]
    assert row["downstream_promotion_allowed"] is False


def test_missing_actor_fields_cannot_compare_as_equal_for_player_role():
    selected_action, selected_event, sequence = payloads()
    del selected_action["selected_action_nodes"][0]["actor_identity_candidate_id"]
    del selected_event["selected_event_consequence_candidates"][0]["actor_identity_candidate_id"]
    row = record(module.build_outcome_support_bridge(selected_action, selected_event, sequence))
    assert "actor_identity_candidate_id_missing_on_selected_action" in row["conflict_reasons"]
    assert "actor_identity_candidate_id_missing_on_selected_event" in row["conflict_reasons"]


def test_explicit_team_actor_null_is_allowed_when_field_is_present():
    selected_action, selected_event, sequence = payloads()
    node = selected_action["selected_action_nodes"][0]
    event = selected_event["selected_event_consequence_candidates"][0]
    node.update(source_role="TEAM_SURFACE_CANDIDATE", actor_identity_candidate_id=None)
    event.update(source_role="TEAM_SURFACE_CANDIDATE", actor_identity_candidate_id=None)
    row = record(module.build_outcome_support_bridge(selected_action, selected_event, sequence))
    assert row["outcome_support_classification"] == "VISIBLE_CONSEQUENCE_SUPPORT_ONLY"
    assert not any("actor_identity" in reason for reason in row["conflict_reasons"])


def test_blank_team_actor_ids_are_not_explicit_null():
    selected_action, selected_event, sequence = payloads()
    node = selected_action["selected_action_nodes"][0]
    event = selected_event["selected_event_consequence_candidates"][0]
    node.update(source_role="TEAM_SURFACE_CANDIDATE", actor_identity_candidate_id="")
    event.update(source_role="TEAM_SURFACE_CANDIDATE", actor_identity_candidate_id="   ")
    row = record(module.build_outcome_support_bridge(selected_action, selected_event, sequence))
    assert "actor_identity_candidate_id_blank_on_selected_action" in row["conflict_reasons"]
    assert "actor_identity_candidate_id_blank_on_selected_event" in row["conflict_reasons"]
    assert row["downstream_promotion_allowed"] is False


def test_terminal_flag_requires_terminal_atom_class():
    selected_action, selected_event, sequence = payloads(terminal=True)
    selected_action["selected_action_nodes"][0]["support_atom_class_counts"] = {
        "DERIVED_CONSEQUENCE_ATOM": 1
    }
    row = record(module.build_outcome_support_bridge(selected_action, selected_event, sequence))
    assert "terminal_support_flag_without_matching_atom_class" in row["conflict_reasons"]
    assert "derived_atom_class_without_support_flag" in row["conflict_reasons"]


def test_derived_flag_requires_derived_atom_class():
    selected_action, selected_event, sequence = payloads(derived=True)
    selected_action["selected_action_nodes"][0]["support_atom_class_counts"] = {
        "TERMINAL_OUTCOME_ATOM": 1
    }
    row = record(module.build_outcome_support_bridge(selected_action, selected_event, sequence))
    assert "derived_support_flag_without_matching_atom_class" in row["conflict_reasons"]
    assert "terminal_atom_class_without_support_flag" in row["conflict_reasons"]


def test_support_atom_counts_must_reconcile_with_ids():
    selected_action, selected_event, sequence = payloads(terminal=True)
    selected_action["selected_action_nodes"][0]["support_atom_class_counts"] = {
        "TERMINAL_OUTCOME_ATOM": 2
    }
    row = record(module.build_outcome_support_bridge(selected_action, selected_event, sequence))
    assert "support_atom_count_id_mismatch" in row["conflict_reasons"]


def test_missing_selected_event_consequence_class_conflicts_even_with_terminal_support():
    selected_action, selected_event, sequence = payloads(terminal=True)
    del selected_event["selected_event_consequence_candidates"][0]["consequence_class_candidate"]
    row = record(module.build_outcome_support_bridge(selected_action, selected_event, sequence))
    assert "consequence_class_candidate_missing_on_selected_event" in row["conflict_reasons"]
    assert row["downstream_promotion_allowed"] is False


def test_missing_sequence_payload_binding_fails_closed_without_sequence_admission():
    selected_action, selected_event, sequence = payloads(sequence=True)
    del sequence["match_surface_binding_id"]
    result = module.build_outcome_support_bridge(selected_action, selected_event, sequence)
    row = record(result)
    assert result["status"] == "FAIL_CLOSED"
    assert result["payload_binding_gate_pass"] is False
    assert result["module_hard_block_gate_pass"] is False
    assert result["sequence_supported_anchor_count"] == 0
    assert row["sequence_metric_evidence_anchor_support"] == []
    assert row["outcome_support_classification"] == "CONFLICTED_OUTCOME_SUPPORT"
    assert "payload_binding_gate_failed" in row["conflict_reasons"]
    assert "module_hard_block_gate_failed" in row["conflict_reasons"]
    assert row["downstream_promotion_allowed"] is False


def test_mismatched_sequence_binding_cannot_create_multi_source_promotion():
    selected_action, selected_event, sequence = payloads(sequence=True)
    sequence["match_surface_binding_id"] = "msb_other"
    result = module.build_outcome_support_bridge(selected_action, selected_event, sequence)
    row = record(result)
    assert result["status"] == "FAIL_CLOSED"
    assert result["payload_binding_gate_pass"] is False
    assert result["module_hard_block_gate_pass"] is False
    assert result["sequence_supported_anchor_count"] == 0
    assert row["sequence_metric_evidence_anchor_support"] == []
    assert row["outcome_support_classification"] == "CONFLICTED_OUTCOME_SUPPORT"
    assert row["downstream_promotion_allowed"] is False


def test_missing_selected_event_coverage_fails_closed():
    selected_action, selected_event, sequence = payloads()
    selected_event["selected_event_consequence_candidates"] = []
    selected_event["selected_event_consequence_candidate_count"] = 0
    result = module.build_outcome_support_bridge(selected_action, selected_event, sequence)
    assert result["status"] == "FAIL_CLOSED"
    assert result["module_hard_block_gate_pass"] is False
    assert any(hit.startswith("selected_event_coverage_missing") for hit in result["hard_block_hits"])


def test_sequence_anchor_reference_must_exist():
    selected_action, selected_event, sequence = payloads(sequence=True)
    sequence["metric_records"][0]["evidence_anchor_node_ids"] = ["missing"]
    result = module.build_outcome_support_bridge(selected_action, selected_event, sequence)
    assert result["status"] == "FAIL_CLOSED"
    assert result["module_hard_block_gate_pass"] is False
    assert any(
        hit.startswith("sequence_metric_anchor_reference_missing")
        for hit in result["hard_block_hits"]
    )


def test_explicit_support_requires_atom_lineage():
    selected_action, selected_event, sequence = payloads(terminal=True)
    selected_action["selected_action_nodes"][0]["supporting_evidence_atom_ids"] = []
    row = record(module.build_outcome_support_bridge(selected_action, selected_event, sequence))
    assert "support_atom_count_id_mismatch" in row["conflict_reasons"]


def test_blank_and_null_atom_ids_conflict_before_reconciliation():
    selected_action, selected_event, sequence = payloads(terminal=True)
    selected_action["selected_action_nodes"][0]["supporting_evidence_atom_ids"] = [
        "atom_terminal",
        "   ",
        None,
    ]
    row = record(module.build_outcome_support_bridge(selected_action, selected_event, sequence))
    assert "supporting_evidence_atom_id_invalid:1" in row["conflict_reasons"]
    assert "supporting_evidence_atom_id_invalid:2" in row["conflict_reasons"]
    assert row["outcome_support_classification"] == "CONFLICTED_OUTCOME_SUPPORT"
    assert row["downstream_promotion_allowed"] is False


def test_module_hard_block_prevents_all_record_promotion():
    selected_action, selected_event, sequence = payloads(terminal=True, sequence=True)
    selected_action["hard_block_hits"] = ["upstream_integrity_failure"]
    result = module.build_outcome_support_bridge(selected_action, selected_event, sequence)
    row = record(result)
    assert result["status"] == "FAIL_CLOSED"
    assert result["module_hard_block_gate_pass"] is False
    assert "selected_action_hard_blocks_present" in result["hard_block_hits"]
    assert "module_hard_block_gate_failed" in row["conflict_reasons"]
    assert row["outcome_support_classification"] == "CONFLICTED_OUTCOME_SUPPORT"
    assert row["downstream_outcome_support_status"] == "CONFLICTED"
    assert row["downstream_promotion_allowed"] is False
    assert not any(
        candidate["downstream_promotion_allowed"]
        for candidate in result["outcome_support_bridge_records"]
    )


def test_normalized_atom_class_key_collision_conflicts():
    selected_action, selected_event, sequence = payloads(terminal=True)
    selected_action["selected_action_nodes"][0]["support_atom_class_counts"] = {
        " TERMINAL_OUTCOME_ATOM": 1,
        "TERMINAL_OUTCOME_ATOM": 1,
    }
    row = record(module.build_outcome_support_bridge(selected_action, selected_event, sequence))
    assert (
        "support_atom_class_key_normalization_collision:TERMINAL_OUTCOME_ATOM"
        in row["conflict_reasons"]
    )
    assert row["outcome_support_classification"] == "CONFLICTED_OUTCOME_SUPPORT"
    assert row["downstream_promotion_allowed"] is False


def test_nested_phone_output_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="nested_phone_output_directory_rejected"):
        module.validate_out(tmp_path / "HPFA" / "nested")


def test_no_metric_rate_output():
    result = build()
    assert result["metric_rate_output_allowed"] is False
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["production_release"] is False
    assert result["version"] == "1.0.4"
