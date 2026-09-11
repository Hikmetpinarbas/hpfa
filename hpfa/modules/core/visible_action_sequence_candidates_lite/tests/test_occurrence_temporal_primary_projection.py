from __future__ import annotations

import visible_action_sequence_candidates_current_v1 as current


def _legacy_layer() -> dict:
    return {
        "visible_action_time_layer_candidate_id": "legacy_layer",
        "match_surface_binding_id": "binding_generic",
        "period_candidate": "1",
        "start_candidate": 10.0,
        "layer_state": "SINGLE_TEAM_PRIMARY_LAYER",
        "same_timestamp_internal_ordering_allowed": False,
        "time_layer_is_event_group_truth": False,
        "time_layer_is_sequence_truth": False,
        "canonical_event_count": "UNKNOWN",
    }


def _legacy_sequence() -> dict:
    return {
        "visible_action_sequence_candidate_id": "legacy_sequence",
        "sequence_record_status": "REVIEW_REQUIRED_CONTEXT",
        "trackable_action_trace_candidate_ids": ["legacy_trace"],
        "canonical_event_count": "UNKNOWN",
        "claim_ceiling": "VISIBLE_SEQUENCE_CANDIDATE_ONLY",
    }


def _occurrence_layer(layer_id: str, start: float) -> dict:
    return {
        "visible_action_time_layer_candidate_id": layer_id,
        "match_surface_binding_id": "binding_generic",
        "period_candidate": "1",
        "start_candidate": start,
        "layer_state": "SINGLE_TEAM_PRIMARY_LAYER",
        "supporting_action_occurrence_candidate_ids": [f"occ_{layer_id}"],
        "trackable_action_trace_candidate_ids": [f"trace_{layer_id}"],
        "same_timestamp_internal_ordering_allowed": False,
        "time_layer_is_event_group_truth": False,
        "time_layer_is_sequence_truth": False,
        "canonical_event_count": "UNKNOWN",
    }


def _occurrence_sequence() -> dict:
    return {
        "visible_action_sequence_candidate_id": "occurrence_sequence",
        "match_surface_binding_id": "binding_generic",
        "period_candidate": "1",
        "time_layer_candidate_ids": ["occ_layer_a", "occ_layer_b"],
        "time_layer_count": 2,
        "trackable_action_trace_candidate_ids": ["trace_occ_layer_a", "trace_occ_layer_b"],
        "supporting_action_occurrence_candidate_ids": ["occ_a", "occ_b"],
        "trace_candidate_count": 2,
        "sequence_record_status": "PASS_MULTI_LAYER_VISIBLE_SEQUENCE_CANDIDATE",
        "consequence_review_trace_count": 0,
        "visible_sequence_candidate_is_sequence_truth": False,
        "visible_sequence_candidate_is_possession_truth": False,
        "single_team_continuity_is_control_truth": False,
        "sequence_duration_is_physical_action_duration": False,
        "same_timestamp_internal_ordering_allowed": False,
        "source_row_order_is_temporal_truth": False,
        "canonical_event_count": "UNKNOWN",
        "claim_ceiling": "VISIBLE_SEQUENCE_CANDIDATE_ONLY",
    }


def _payload() -> dict:
    return {
        "status": "REVIEW_REQUIRED",
        "module_status": "REVIEW_REQUIRED",
        "visible_action_time_layer_candidates": [_legacy_layer()],
        "visible_action_time_layer_candidate_count": 1,
        "visible_action_sequence_candidates": [_legacy_sequence()],
        "visible_action_sequence_candidate_count": 1,
        "source_trackable_action_trace_candidate_count": 100,
        "occurrence_temporal_projection_status": "PASS",
        "occurrence_temporal_time_layer_candidates": [
            _occurrence_layer("occ_layer_a", 10.0),
            _occurrence_layer("occ_layer_b", 14.0),
        ],
        "occurrence_temporal_sequence_candidates": [_occurrence_sequence()],
        "review_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def test_occurrence_temporal_projection_becomes_primary_inventory_and_legacy_is_retained() -> None:
    result = current._promote_occurrence_temporal_primary(_payload())
    assert result["primary_sequence_projection_mode"] == "OCCURRENCE_TEMPORAL_PRIMARY"
    assert result["occurrence_temporal_primary_inventory_admitted"] is True
    assert result["visible_action_sequence_candidate_count"] == 1
    assert result["visible_action_sequence_candidates"][0]["visible_action_sequence_candidate_id"] == "occurrence_sequence"
    assert result["legacy_visible_action_sequence_candidate_count"] == 1
    assert result["legacy_visible_action_sequence_candidates"][0]["visible_action_sequence_candidate_id"] == "legacy_sequence"
    assert result["legacy_trace_sequence_surface_is_primary_action_member_surface"] is False
    assert result["legacy_trace_sequence_surface_retained_as_support_context"] is True
    assert result["pass_multi_layer_visible_sequence_candidate_count"] == 1
    assert result["occurrence_temporal_primary_inventory_is_sequence_truth"] is False
    assert result["occurrence_temporal_primary_inventory_is_possession_truth"] is False
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["true_action_count"] == "UNKNOWN"
    assert result["production_release"] is False


def test_empty_occurrence_projection_does_not_claim_primary_admission() -> None:
    payload = _payload()
    payload["occurrence_temporal_sequence_candidates"] = []
    result = current._promote_occurrence_temporal_primary(payload)
    assert result["occurrence_temporal_primary_inventory_admitted"] is False
    assert result["primary_sequence_projection_mode"] == "LEGACY_TRACE_COMPATIBILITY_EMPTY_OCCURRENCE_PROJECTION"
    assert result["occurrence_temporal_empty_projection_requires_review"] is True
    assert result["visible_action_sequence_candidate_count"] == 1
    assert "occurrence_temporal_primary_inventory_empty" in result["review_hits"]
    assert result["true_action_count"] == "UNKNOWN"


def test_failed_projection_never_replaces_legacy_primary_inventory() -> None:
    payload = _payload()
    payload["occurrence_temporal_projection_status"] = "FAIL_CLOSED"
    result = current._promote_occurrence_temporal_primary(payload)
    assert result["primary_sequence_projection_mode"] == "LEGACY_TRACE_COMPATIBILITY"
    assert result["occurrence_temporal_primary_inventory_admitted"] is False
    assert result["visible_action_sequence_candidates"][0]["visible_action_sequence_candidate_id"] == "legacy_sequence"
