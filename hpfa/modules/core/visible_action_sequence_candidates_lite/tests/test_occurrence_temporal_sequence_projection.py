from __future__ import annotations

from hpfa.modules.core.visible_action_sequence_candidates_lite.src.occurrence_temporal_sequence_projection import (
    build_occurrence_temporal_sequence_projection,
)

BINDING = "msb_" + "s" * 24


def _trace_payload(*, follow_occurrence: bool = True, follow_team: str = "team_a") -> dict:
    follow_occurrences = ["occ_b"] if follow_occurrence else []
    return {
        "module_id": "trackable_action_trace_candidates_lite_v1",
        "match_surface_binding_id": BINDING,
        "trackable_action_trace_candidates": [
            {
                "trackable_action_trace_candidate_id": "trace_a",
                "match_surface_binding_id": BINDING,
                "team_identity_candidate_id": "team_a",
                "actor_identity_candidate_id": "actor_a",
                "period_candidate": "1",
                "start_candidate": "10.0",
                "action_family_candidates": ["PASS"],
                "supporting_action_occurrence_candidate_ids": ["occ_a"],
                "reflection_context_action_bundle_candidate_ids": [],
            },
            {
                "trackable_action_trace_candidate_id": "trace_b",
                "match_surface_binding_id": BINDING,
                "team_identity_candidate_id": follow_team,
                "actor_identity_candidate_id": "actor_b",
                "period_candidate": "1",
                "start_candidate": "15.0",
                "action_family_candidates": ["PASS"],
                "supporting_action_occurrence_candidate_ids": follow_occurrences,
                "reflection_context_action_bundle_candidate_ids": [],
            },
        ],
        "occurrence_trace_binding_records": [
            {
                "action_occurrence_candidate_id": "occ_a",
                "occurrence_topology": "SINGLE_ACTOR_ACTION",
            },
            {
                "action_occurrence_candidate_id": "occ_b",
                "occurrence_topology": "SINGLE_ACTOR_ACTION",
            },
        ],
        "temporal_relation_admission_records": [
            {
                "anchor_trackable_action_trace_candidate_id": "trace_a",
                "candidate_trackable_action_trace_candidate_id": "trace_b",
                "relation_state": "AFTER_CONFIRMED",
            }
        ],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _consequence_payload(*, status: str = "PASS_CANDIDATE_CLASSIFICATION") -> dict:
    return {
        "module_id": "trackable_action_consequence_candidates_lite_v1",
        "match_surface_binding_id": BINDING,
        "trackable_action_consequence_candidates": [
            {
                "trackable_action_consequence_candidate_id": "cons_a",
                "anchor_trackable_action_trace_candidate_id": "trace_a",
                "record_status": status,
                "primary_consequence_candidate": "SAME_TEAM_CONTINUATION_CANDIDATE",
                "admitted_after_follow_up_trace_ids": ["trace_b"],
                "canonical_event_count": "UNKNOWN",
            }
        ],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def test_occurrence_backed_after_confirmed_same_team_continuation_builds_two_layer_candidate() -> None:
    result = build_occurrence_temporal_sequence_projection(_trace_payload(), _consequence_payload())

    assert result["status"] == "PASS"
    assert result["eligible_occurrence_after_confirmed_edge_count"] == 1
    assert result["occurrence_temporal_time_layer_candidate_count"] == 2
    assert result["occurrence_temporal_sequence_candidate_count"] == 1
    sequence = result["occurrence_temporal_sequence_candidates"][0]
    assert sequence["time_layer_count"] == 2
    assert sequence["sequence_record_status"] == "PASS_MULTI_LAYER_VISIBLE_SEQUENCE_CANDIDATE"
    assert sequence["supporting_action_occurrence_candidate_ids"] == ["occ_a", "occ_b"]
    assert sequence["visible_sequence_candidate_is_sequence_truth"] is False
    assert sequence["visible_sequence_candidate_is_possession_truth"] is False
    assert sequence["same_timestamp_internal_ordering_allowed"] is False
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["true_action_count"] == "UNKNOWN"
    assert result["production_release"] is False


def test_missing_follow_occurrence_keeps_sequence_closed() -> None:
    result = build_occurrence_temporal_sequence_projection(
        _trace_payload(follow_occurrence=False),
        _consequence_payload(),
    )

    assert result["occurrence_temporal_sequence_candidate_count"] == 0
    assert result["rejected_edge_reason_counts"]["follow_occurrence_missing"] == 1
    assert result["sequence_truth"] is False


def test_cross_team_followup_cannot_become_same_team_sequence_candidate() -> None:
    result = build_occurrence_temporal_sequence_projection(
        _trace_payload(follow_team="team_b"),
        _consequence_payload(),
    )

    assert result["occurrence_temporal_sequence_candidate_count"] == 0
    assert result["rejected_edge_reason_counts"]["same_team_requirement_failed"] == 1
    assert result["possession_truth"] is False
    assert result["tactical_truth"] is False


def test_review_required_consequence_is_not_promoted_to_sequence_candidate() -> None:
    result = build_occurrence_temporal_sequence_projection(
        _trace_payload(),
        _consequence_payload(status="REVIEW_REQUIRED"),
    )

    assert result["occurrence_temporal_sequence_candidate_count"] == 0
    assert result["causal_truth"] is False


def test_same_timestamp_occurrences_remain_unordered_within_layer() -> None:
    trace = _trace_payload()
    trace["trackable_action_trace_candidates"].insert(
        1,
        {
            "trackable_action_trace_candidate_id": "trace_a2",
            "match_surface_binding_id": BINDING,
            "team_identity_candidate_id": "team_a",
            "actor_identity_candidate_id": "actor_a2",
            "period_candidate": "1",
            "start_candidate": "10.0",
            "action_family_candidates": ["PASS"],
            "supporting_action_occurrence_candidate_ids": ["occ_a2"],
            "reflection_context_action_bundle_candidate_ids": [],
        },
    )
    trace["occurrence_trace_binding_records"].append(
        {"action_occurrence_candidate_id": "occ_a2", "occurrence_topology": "SINGLE_ACTOR_ACTION"}
    )
    trace["temporal_relation_admission_records"].append(
        {
            "anchor_trackable_action_trace_candidate_id": "trace_a2",
            "candidate_trackable_action_trace_candidate_id": "trace_b",
            "relation_state": "AFTER_CONFIRMED",
        }
    )
    consequence = _consequence_payload()
    consequence["trackable_action_consequence_candidates"].append(
        {
            "trackable_action_consequence_candidate_id": "cons_a2",
            "anchor_trackable_action_trace_candidate_id": "trace_a2",
            "record_status": "PASS_CANDIDATE_CLASSIFICATION",
            "primary_consequence_candidate": "SAME_TEAM_CONTINUATION_CANDIDATE",
            "admitted_after_follow_up_trace_ids": ["trace_b"],
            "canonical_event_count": "UNKNOWN",
        }
    )

    result = build_occurrence_temporal_sequence_projection(trace, consequence)
    sequence = result["occurrence_temporal_sequence_candidates"][0]
    source_layer_id = sequence["time_layer_candidate_ids"][0]
    source_layer = next(
        row for row in result["occurrence_temporal_time_layer_candidates"]
        if row["visible_action_time_layer_candidate_id"] == source_layer_id
    )
    assert source_layer["supporting_action_occurrence_candidate_ids"] == ["occ_a", "occ_a2"]
    assert source_layer["same_timestamp_internal_ordering_allowed"] is False
    assert sequence["supporting_after_confirmed_edge_count"] == 2
