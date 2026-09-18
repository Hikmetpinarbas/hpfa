from __future__ import annotations

from hpfa.modules.core.trackable_action_trace_candidates_lite.src.occurrence_topology_adapter import (
    apply_occurrence_topology_binding,
)


def test_single_actor_occurrence_requires_actor_trace_only() -> None:
    trace = {
        "status": "REVIEW_REQUIRED",
        "module_status": "REVIEW_REQUIRED",
        "occurrence_trace_binding_records": [
            {
                "action_occurrence_candidate_id": "occ_pass",
                "binding_state": "PARTIAL_PARTICIPANT_TRACE_VISIBLE_REVIEW_REQUIRED",
                "actor_trace_candidate_count": 1,
                "opponent_trace_candidate_count": 0,
                "total_occurrence_bound_trace_candidate_count": 1,
            }
        ],
        "review_hits": ["occurrence_partial_participant_trace_binding_present"],
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }
    occurrence = {
        "action_occurrence_candidates": [
            {
                "action_occurrence_candidate_id": "occ_pass",
                "occurrence_topology": "SINGLE_ACTOR_ACTION",
                "actor_identity_candidate_id": "actor_a",
                "opponent_identity_candidate_id": None,
            }
        ]
    }

    result = apply_occurrence_topology_binding(trace, occurrence)
    record = result["occurrence_trace_binding_records"][0]
    assert record["binding_state"] == "SINGLE_ACTOR_TRACE_VISIBLE_CANDIDATE"
    assert record["required_participant_scope"] == "ACTOR_ONLY"
    assert result["occurrence_single_actor_trace_visible_count"] == 1
    assert result["occurrence_partial_participant_trace_visible_count"] == 0
    assert "occurrence_partial_participant_trace_binding_present" not in result["review_hits"]
    assert result["status"] == "PASS"


def test_two_participant_interaction_still_requires_actor_and_opponent() -> None:
    trace = {
        "status": "PASS",
        "module_status": "PASS",
        "occurrence_trace_binding_records": [
            {
                "action_occurrence_candidate_id": "occ_duel",
                "actor_trace_candidate_count": 1,
                "opponent_trace_candidate_count": 0,
                "total_occurrence_bound_trace_candidate_count": 1,
            }
        ],
        "review_hits": [],
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }
    occurrence = {
        "action_occurrence_candidates": [
            {
                "action_occurrence_candidate_id": "occ_duel",
                "actor_identity_candidate_id": "actor_a",
                "opponent_identity_candidate_id": "actor_b",
            }
        ]
    }

    result = apply_occurrence_topology_binding(trace, occurrence)
    record = result["occurrence_trace_binding_records"][0]
    assert record["occurrence_topology"] == "TWO_PARTICIPANT_INTERACTION"
    assert record["required_participant_scope"] == "ACTOR_AND_OPPONENT"
    assert result["occurrence_single_actor_trace_visible_count"] == 0
    assert result["occurrence_partial_participant_trace_visible_count"] == 1
    assert "occurrence_partial_participant_trace_binding_present" in result["review_hits"]
    assert result["status"] == "REVIEW_REQUIRED"


def test_primary_trace_surface_contains_only_occurrence_backed_members() -> None:
    trace = {
        "status": "PASS",
        "module_status": "PASS",
        "occurrence_trace_binding_records": [],
        "trackable_action_trace_candidates": [
            {
                "trackable_action_trace_candidate_id": "trace_bound",
                "supporting_action_occurrence_candidate_ids": ["occ_1"],
            },
            {
                "trackable_action_trace_candidate_id": "trace_legacy_unbound",
                "supporting_action_occurrence_candidate_ids": [],
            },
        ],
        "review_hits": [],
    }

    result = apply_occurrence_topology_binding(
        trace,
        {"action_occurrence_candidates": [{"action_occurrence_candidate_id": "occ_1"}]},
    )

    assert result["source_legacy_trace_candidate_count"] == 2
    assert result["primary_occurrence_trace_candidate_count"] == 1
    assert result["legacy_unbound_trace_candidate_count"] == 1
    assert [
        row["trackable_action_trace_candidate_id"]
        for row in result["primary_occurrence_trace_candidates"]
    ] == ["trace_bound"]
    assert result["trackable_action_trace_candidates"][0]["primary_occurrence_member_candidate"] is True
    assert result["trackable_action_trace_candidates"][1]["legacy_unbound_support_only"] is True
    assert result["legacy_trace_records_are_primary_action_member_surface"] is False
    assert result["legacy_unbound_trace_records_retained_as_support_only"] is True


def test_claim_locks_remain_closed() -> None:
    trace = {
        "status": "PASS",
        "module_status": "PASS",
        "occurrence_trace_binding_records": [],
        "review_hits": [],
    }
    result = apply_occurrence_topology_binding(trace, {"action_occurrence_candidates": []})
    assert result["occurrence_topology_aware_binding"] is True
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["true_action_count"] == "UNKNOWN"
    assert result["production_release"] is False
