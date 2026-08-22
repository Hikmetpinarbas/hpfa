from __future__ import annotations

import json
from pathlib import Path

from hpfa.modules.core.visible_action_sequence_candidates_lite.src.visible_action_sequence_candidates import (
    build_visible_action_sequence_candidates,
)

BINDING = "msb_" + "a" * 24
TEAM_A = "teamc_a"
TEAM_B = "teamc_b"


def _trace(
    trace_id: str,
    *,
    team: str = TEAM_A,
    actor: str = "actor_a",
    start: float = 10.0,
    period: str = "1",
    family: str = "PASS",
) -> dict:
    return {
        "trackable_action_trace_candidate_id": trace_id,
        "match_surface_binding_id": BINDING,
        "source_role": "PLAYER_SURFACE_CANDIDATE",
        "team_identity_candidate_id": team,
        "actor_identity_candidate_id": actor,
        "period_candidate": period,
        "start_candidate": str(start),
        "end_candidate": str(start + 0.5),
        "pos_x_candidate": "10",
        "pos_y_candidate": "20",
        "action_family_candidates": [family],
        "reflection_context_action_bundle_candidate_ids": [f"reflection_{trace_id}"],
        "trackable_action_candidate_is_event_truth": False,
        "physical_action_identity_truth": False,
        "sequence_link_allowed": False,
        "canonical_event_count": "UNKNOWN",
    }


def _consequence(trace: dict) -> dict:
    trace_id = trace["trackable_action_trace_candidate_id"]
    return {
        "trackable_action_consequence_candidate_id": f"c_{trace_id}",
        "anchor_trackable_action_trace_candidate_id": trace_id,
        "match_surface_binding_id": BINDING,
        "record_status": "PASS_CANDIDATE_CLASSIFICATION",
        "primary_consequence_candidate": "SAME_TEAM_CONTINUATION_CANDIDATE",
        "terminal_outcome_support_visible": False,
        "same_time_link_allowed": False,
        "negative_time_link_allowed": False,
        "cross_period_link_allowed": False,
        "window_is_sequence_truth": False,
        "continuation_is_possession_truth": False,
        "consequence_candidate_is_causal_truth": False,
        "event_instance_allowed": False,
        "validated_event_identity": False,
        "canonical_event_count": "UNKNOWN",
    }


def _build(traces: list[dict]) -> dict:
    trace_payload = {
        "module_id": "trackable_action_trace_candidates_lite_v1",
        "module_status": "PASS",
        "status": "PASS",
        "match_surface_binding_id": BINDING,
        "trackable_action_trace_candidates": traces,
        "trackable_action_trace_candidate_count": len(traces),
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }
    consequences = [_consequence(trace) for trace in traces]
    consequence_payload = {
        "module_id": "trackable_action_consequence_candidates_lite_v1",
        "module_status": "PASS",
        "status": "PASS",
        "match_surface_binding_id": BINDING,
        "trackable_action_consequence_candidates": consequences,
        "trackable_action_consequence_candidate_count": len(consequences),
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }
    return build_visible_action_sequence_candidates(trace_payload, consequence_payload)


def test_same_timestamp_no_artificial_order() -> None:
    result = _build([
        _trace("a", start=10.0, actor="actor_a"),
        _trace("b", start=10.0, actor="actor_b", family="CARRY"),
    ])
    layer = result["visible_action_time_layer_candidates"][0]
    assert result["visible_action_time_layer_candidate_count"] == 1
    assert layer["trace_candidate_count"] == 2
    assert layer["same_timestamp_internal_ordering_allowed"] is False
    assert result["source_row_order_is_temporal_truth"] is False


def test_same_timestamp_input_permutation_is_invariant() -> None:
    a = _trace("a", start=10.0, actor="actor_a")
    b = _trace("b", start=10.0, actor="actor_b", family="CARRY")
    first = _build([a, b])
    second = _build([b, a])
    assert first["visible_action_time_layer_candidates"] == second["visible_action_time_layer_candidates"]
    assert first["visible_action_sequence_candidates"] == second["visible_action_sequence_candidates"]
    assert first["trace_assignments"] == second["trace_assignments"]


def test_mixed_team_same_timestamp_fails_closed_to_review_layer() -> None:
    result = _build([
        _trace("a", start=10.0, team=TEAM_A, actor="actor_a"),
        _trace("b", start=10.0, team=TEAM_B, actor="actor_b"),
    ])
    assert result["mixed_team_primary_layer_review_required_count"] == 1
    assert result["visible_action_sequence_candidate_count"] == 0
    assert result["review_layer_member_trace_count"] == 2
    assert result["trace_assignment_complete"] is True
    assert result["sequence_truth"] is False
    assert result["possession_truth"] is False


def test_strictly_later_visible_time_does_not_promote_directly_follows_truth() -> None:
    result = _build([
        _trace("a", start=10.0, actor="actor_a"),
        _trace("b", start=14.0, actor="actor_b"),
    ])
    assert result["visible_action_sequence_candidate_count"] == 1
    sequence = result["visible_action_sequence_candidates"][0]
    assert sequence["time_layer_count"] == 2
    assert result["strict_positive_inter_layer_time_required"] is True
    assert result["visible_sequence_candidate_is_sequence_truth"] is False
    assert result["sequence_truth"] is False
    assert result["consequence_context_is_causal_truth"] is False


def test_partial_order_contract_vocabulary_and_claim_locks() -> None:
    path = Path(
        "hpfa/modules/core/visible_action_sequence_candidates_lite/contract/"
        "visible_action_sequence_candidates_lite_v1.json"
    )
    contract = json.loads(path.read_text(encoding="utf-8"))
    partial = contract["partial_order_audit"]
    assert partial["relation_states"] == [
        "BEFORE_CONFIRMED",
        "AFTER_CONFIRMED",
        "SAME_TIME_UNORDERED",
        "ORDER_INDETERMINATE",
        "PROVENANCE_ORDER_ONLY",
    ]
    assert partial["ordering_evidence_scope"] == "VISIBLE_TIMESTAMP_ONLY"
    assert partial["same_timestamp_default"] == "SAME_TIME_UNORDERED"
    assert partial["missing_or_ambiguous_order_default"] == "ORDER_INDETERMINATE"
    assert partial["source_row_index_relation"] == "PROVENANCE_ORDER_ONLY"
    assert partial["directly_follows_truth"] is False
    assert partial["relation_records_may_create_action_volume"] is False
    assert partial["relation_records_may_create_possession_truth"] is False
    assert partial["relation_records_may_create_sequence_truth"] is False
