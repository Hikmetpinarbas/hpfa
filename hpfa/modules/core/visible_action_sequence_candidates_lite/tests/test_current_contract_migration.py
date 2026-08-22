from __future__ import annotations

from pathlib import Path

import pytest

from hpfa.modules.core.visible_action_sequence_candidates_lite.src.visible_action_sequence_candidates import (
    build_visible_action_sequence_candidates,
    validate_out,
)

BINDING = "msb_" + "a" * 24
TEAM_A = "teamc_a"
TEAM_B = "teamc_b"


def trace(trace_id: str, *, team: str = TEAM_A, actor: str = "actor_a", start: float = 10.0, period: str = "1", family: str = "PASS", role: str = "PLAYER_SURFACE_CANDIDATE") -> dict:
    return {
        "trackable_action_trace_candidate_id": trace_id,
        "match_surface_binding_id": BINDING,
        "source_role": role,
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


def consequence(t: dict, *, status: str = "PASS_CANDIDATE_CLASSIFICATION", primary: str = "SAME_TEAM_CONTINUATION_CANDIDATE", terminal: bool = False) -> dict:
    trace_id = t["trackable_action_trace_candidate_id"]
    return {
        "trackable_action_consequence_candidate_id": f"c_{trace_id}",
        "anchor_trackable_action_trace_candidate_id": trace_id,
        "match_surface_binding_id": BINDING,
        "record_status": status,
        "primary_consequence_candidate": primary,
        "terminal_outcome_support_visible": terminal,
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


def payloads(traces: list[dict], consequences: list[dict] | None = None) -> tuple[dict, dict]:
    consequences = consequences if consequences is not None else [consequence(t) for t in traces]
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
    return trace_payload, consequence_payload


def build(traces: list[dict], consequences: list[dict] | None = None) -> dict:
    return build_visible_action_sequence_candidates(*payloads(traces, consequences))


def test_same_team_same_timestamp_is_one_layer_without_internal_order() -> None:
    result = build([trace("a", start=10), trace("b", start=10, actor="actor_b", family="CARRY")])
    assert result["visible_action_time_layer_candidate_count"] == 1
    layer = result["visible_action_time_layer_candidates"][0]
    assert layer["layer_state"] == "SINGLE_TEAM_PRIMARY_LAYER"
    assert layer["trace_candidate_count"] == 2
    assert layer["same_timestamp_internal_ordering_allowed"] is False
    assert result["visible_action_sequence_candidate_count"] == 1


def test_mixed_team_same_timestamp_is_review_layer_not_sequence() -> None:
    result = build([trace("a", start=10, team=TEAM_A), trace("b", start=10, team=TEAM_B, actor="actor_b")])
    assert result["mixed_team_primary_layer_review_required_count"] == 1
    assert result["visible_action_sequence_candidate_count"] == 0
    assert result["review_layer_member_trace_count"] == 2
    assert result["trace_assignment_complete"] is True


def test_same_team_positive_gap_within_ceiling_forms_multi_layer_sequence() -> None:
    result = build([trace("a", start=10), trace("b", start=14, actor="actor_b")])
    assert result["visible_action_sequence_candidate_count"] == 1
    seq = result["visible_action_sequence_candidates"][0]
    assert seq["time_layer_count"] == 2
    assert seq["sequence_record_status"] == "PASS_MULTI_LAYER_VISIBLE_SEQUENCE_CANDIDATE"


def test_gap_above_12_seconds_splits_sequence() -> None:
    result = build([trace("a", start=10), trace("b", start=22.1, actor="actor_b")])
    assert result["visible_action_sequence_candidate_count"] == 2
    assert result["boundary_reason_counts"]["TIME_GAP_BOUNDARY"] == 1


def test_team_handover_splits_sequence() -> None:
    result = build([trace("a", start=10, team=TEAM_A), trace("b", start=14, team=TEAM_B, actor="actor_b")])
    assert result["visible_action_sequence_candidate_count"] == 2
    assert result["boundary_reason_counts"]["TEAM_HANDOVER_BOUNDARY"] == 1
    assert len(result["visible_sequence_boundary_candidates"]) == 1
    assert result["visible_sequence_boundary_candidates"][0]["boundary_is_possession_change_truth"] is False


def test_restart_primary_layer_splits_before_restart() -> None:
    result = build([trace("a", start=10), trace("b", start=14, actor="actor_b", family="RESTART")])
    assert result["visible_action_sequence_candidate_count"] == 2
    assert result["boundary_reason_counts"]["RESTART_PRIMARY_LAYER_BOUNDARY"] == 1


def test_terminal_support_closes_sequence_after_layer() -> None:
    a = trace("a", start=10)
    b = trace("b", start=14, actor="actor_b")
    result = build([a, b], [consequence(a, terminal=True), consequence(b)])
    assert result["visible_action_sequence_candidate_count"] == 2
    assert result["boundary_reason_counts"]["TERMINAL_OUTCOME_SUPPORT_BOUNDARY"] == 1


def test_period_change_never_links_across_periods() -> None:
    result = build([trace("a", start=100, period="1"), trace("b", start=1, period="2", actor="actor_b")])
    assert result["visible_action_sequence_candidate_count"] == 2
    assert all(seq["time_layer_count"] == 1 for seq in result["visible_action_sequence_candidates"])


def test_consequence_review_marks_sequence_context_review_without_order_truth() -> None:
    a = trace("a", start=10)
    b = trace("b", start=14, actor="actor_b")
    review = consequence(a, status="REVIEW_REQUIRED", primary="MIXED_TEAM_SAME_TIME_FOLLOW_UP_REVIEW_REQUIRED_CANDIDATE")
    result = build([a, b], [review, consequence(b)])
    assert result["visible_action_sequence_candidate_count"] == 1
    assert result["review_required_sequence_context_count"] == 1
    assert result["visible_action_sequence_candidates"][0]["sequence_record_status"] == "REVIEW_REQUIRED_CONTEXT"
    assert result["same_timestamp_internal_ordering_allowed"] is False


def test_every_trace_has_exactly_one_assignment() -> None:
    traces = [trace("a", start=10), trace("b", start=14, actor="actor_b"), trace("c", start=20, team=TEAM_B, actor="actor_c")]
    result = build(traces)
    ids = [row["trackable_action_trace_candidate_id"] for row in result["trace_assignments"]]
    assert len(ids) == len(set(ids)) == len(traces)
    assert result["trace_assignment_complete"] is True


def test_duplicate_consequence_anchor_fails_closed() -> None:
    a = trace("a")
    c1 = consequence(a)
    c2 = dict(c1)
    c2["trackable_action_consequence_candidate_id"] = "c_other"
    result = build(a and [a], [c1, c2])
    assert result["status"] == "FAIL_CLOSED"
    assert any(hit.startswith("duplicate_consequence_anchor_trace_id") for hit in result["hard_block_hits"])


def test_missing_actor_trace_fails_closed() -> None:
    a = trace("a", actor="")
    result = build([a])
    assert result["status"] == "FAIL_CLOSED"
    assert any(hit.startswith("trace_actor_identity_candidate_missing") for hit in result["hard_block_hits"])


def test_team_surface_trace_is_rejected() -> None:
    a = trace("a", role="TEAM_SURFACE_CANDIDATE", actor="")
    result = build([a])
    assert result["status"] == "FAIL_CLOSED"
    assert any(hit.startswith("trace_source_role_rejected") for hit in result["hard_block_hits"])


def test_claim_boundaries_remain_closed() -> None:
    result = build([trace("a")])
    assert result["visible_sequence_candidate_is_sequence_truth"] is False
    assert result["visible_sequence_candidate_is_possession_truth"] is False
    assert result["single_team_continuity_is_control_truth"] is False
    assert result["source_row_order_is_temporal_truth"] is False
    assert result["sequence_truth"] is False
    assert result["possession_truth"] is False
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["true_action_count"] == "UNKNOWN"
    assert result["production_release"] is False


def test_nested_phone_output_rejected() -> None:
    with pytest.raises(ValueError, match="nested_phone_output_directory_rejected"):
        validate_out(Path("/sdcard/Download/HPFA/nested"))


def test_no_sample_match_identity_leak() -> None:
    source = Path("hpfa/modules/core/visible_action_sequence_candidates_lite/src/visible_action_sequence_candidates.py").read_text(encoding="utf-8")
    for token in ("Genclerbirligi", "Fenerbahce", "15.08.2026"):
        assert token not in source
