from __future__ import annotations

from hpfa.modules.core.visible_action_sequence_candidates_lite.src.occurrence_temporal_sequence_projection import (
    build_occurrence_temporal_sequence_projection,
)

BINDING = "msb_" + "p" * 24


def _trace(trace_id: str, occurrence_id: str, start: str) -> dict:
    return {
        "trackable_action_trace_candidate_id": trace_id,
        "match_surface_binding_id": BINDING,
        "team_identity_candidate_id": "team_a",
        "actor_identity_candidate_id": trace_id + "_actor",
        "period_candidate": "1",
        "start_candidate": start,
        "action_family_candidates": ["PASS"],
        "supporting_action_occurrence_candidate_ids": [occurrence_id],
        "reflection_context_action_bundle_candidate_ids": [],
    }


def test_legacy_trace_outside_primary_occurrence_surface_cannot_enter_sequence() -> None:
    anchor = _trace("trace_legacy_anchor", "occ_legacy", "10.0")
    follow = _trace("trace_primary_follow", "occ_primary", "15.0")
    trace_payload = {
        "match_surface_binding_id": BINDING,
        "trackable_action_trace_candidates": [anchor, follow],
        "primary_occurrence_trace_candidates": [follow],
        "occurrence_trace_binding_records": [
            {"action_occurrence_candidate_id": "occ_legacy", "occurrence_topology": "SINGLE_ACTOR_ACTION"},
            {"action_occurrence_candidate_id": "occ_primary", "occurrence_topology": "SINGLE_ACTOR_ACTION"},
        ],
        "temporal_relation_admission_records": [
            {
                "anchor_trackable_action_trace_candidate_id": "trace_legacy_anchor",
                "candidate_trackable_action_trace_candidate_id": "trace_primary_follow",
                "relation_state": "AFTER_CONFIRMED",
            }
        ],
    }
    consequence_payload = {
        "match_surface_binding_id": BINDING,
        "trackable_action_consequence_candidates": [
            {
                "trackable_action_consequence_candidate_id": "cons_legacy",
                "anchor_trackable_action_trace_candidate_id": "trace_legacy_anchor",
                "record_status": "PASS_CANDIDATE_CLASSIFICATION",
                "primary_consequence_candidate": "SAME_TEAM_CONTINUATION_CANDIDATE",
                "admitted_after_follow_up_trace_ids": ["trace_primary_follow"],
            }
        ],
    }

    result = build_occurrence_temporal_sequence_projection(trace_payload, consequence_payload)

    assert result["occurrence_temporal_sequence_candidate_count"] == 0
    assert result["eligible_occurrence_after_confirmed_edge_count"] == 0
    assert result["rejected_edge_reason_counts"]["anchor_trace_missing"] == 1
    assert result["sequence_truth"] is False
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["true_action_count"] == "UNKNOWN"
    assert result["production_release"] is False


def test_legacy_trace_fallback_still_works_when_primary_surface_not_present() -> None:
    anchor = _trace("trace_anchor", "occ_a", "10.0")
    follow = _trace("trace_follow", "occ_b", "15.0")
    trace_payload = {
        "match_surface_binding_id": BINDING,
        "trackable_action_trace_candidates": [anchor, follow],
        "occurrence_trace_binding_records": [
            {"action_occurrence_candidate_id": "occ_a", "occurrence_topology": "SINGLE_ACTOR_ACTION"},
            {"action_occurrence_candidate_id": "occ_b", "occurrence_topology": "SINGLE_ACTOR_ACTION"},
        ],
        "temporal_relation_admission_records": [
            {
                "anchor_trackable_action_trace_candidate_id": "trace_anchor",
                "candidate_trackable_action_trace_candidate_id": "trace_follow",
                "relation_state": "AFTER_CONFIRMED",
            }
        ],
    }
    consequence_payload = {
        "match_surface_binding_id": BINDING,
        "trackable_action_consequence_candidates": [
            {
                "trackable_action_consequence_candidate_id": "cons_a",
                "anchor_trackable_action_trace_candidate_id": "trace_anchor",
                "record_status": "PASS_CANDIDATE_CLASSIFICATION",
                "primary_consequence_candidate": "SAME_TEAM_CONTINUATION_CANDIDATE",
                "admitted_after_follow_up_trace_ids": ["trace_follow"],
            }
        ],
    }

    result = build_occurrence_temporal_sequence_projection(trace_payload, consequence_payload)

    assert result["occurrence_temporal_sequence_candidate_count"] == 1
    assert result["eligible_occurrence_after_confirmed_edge_count"] == 1
