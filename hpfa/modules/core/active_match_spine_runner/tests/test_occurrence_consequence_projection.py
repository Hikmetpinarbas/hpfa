from __future__ import annotations

from hpfa.modules.core.active_match_spine_runner.src.occurrence_consequence_projection import (
    build_occurrence_consequence_projection,
)


def _trace(trace_id: str, occurrence_id: str, actor_id: str, team_id: str) -> dict:
    return {
        "trackable_action_trace_candidate_id": trace_id,
        "supporting_action_occurrence_candidate_ids": [occurrence_id],
        "action_family_candidates": ["DUEL"],
        "actor_identity_candidate_id": actor_id,
        "team_identity_candidate_id": team_id,
        "source_role": "PLAYER_SURFACE_CANDIDATE",
        "period_candidate": "1",
        "start_candidate": "10.0",
        "end_candidate": "12.0",
    }


def _consequence(consequence_id: str, occurrence_id: str, anchor_trace_id: str) -> dict:
    return {
        "trackable_action_consequence_candidate_id": consequence_id,
        "anchor_trackable_action_trace_candidate_id": anchor_trace_id,
        "supporting_action_occurrence_candidate_ids": [occurrence_id],
        "visible_follow_up_trace_ids": ["follow_1"],
        "admitted_after_follow_up_trace_ids": [],
        "consequence_signal_candidates": ["NUMERIC_PROVENANCE_WINDOW_VISIBLE_WITHOUT_AFTER_ADMISSION"],
        "primary_consequence_candidate": "PROVENANCE_WINDOW_ONLY_REVIEW_REQUIRED_CANDIDATE",
        "terminal_outcome_support_visible": False,
        "derived_consequence_support_visible": False,
        "record_status": "REVIEW_REQUIRED",
    }


def test_two_participant_interaction_projects_to_one_occurrence_record() -> None:
    occurrence_id = "aoc_interaction_1"
    trace_payload = {
        "status": "REVIEW_REQUIRED",
        "current_occurrence_candidate_count": 1,
        "trackable_action_trace_candidate_count": 2,
        "occurrence_trace_binding_records": [
            {
                "action_occurrence_candidate_id": occurrence_id,
                "occurrence_topology": "TWO_PARTICIPANT_INTERACTION",
                "required_participant_scope": "ACTOR_AND_OPPONENT",
                "binding_state": "BOTH_PARTICIPANTS_TRACE_VISIBLE_CANDIDATE",
            }
        ],
        "trackable_action_trace_candidates": [
            _trace("trace_actor", occurrence_id, "actor_a", "team_a"),
            _trace("trace_opponent", occurrence_id, "actor_b", "team_b"),
        ],
    }
    consequence_payload = {
        "status": "REVIEW_REQUIRED",
        "trackable_action_consequence_candidate_count": 2,
        "trackable_action_consequence_candidates": [
            _consequence("cons_a", occurrence_id, "trace_actor"),
            _consequence("cons_b", occurrence_id, "trace_opponent"),
        ],
    }

    payload = build_occurrence_consequence_projection(trace_payload, consequence_payload)

    assert payload["occurrence_consequence_projection_count"] == 1
    assert payload["source_legacy_trace_candidate_count"] == 2
    record = payload["occurrence_consequence_projections"][0]
    assert record["action_occurrence_candidate_id"] == occurrence_id
    assert record["occurrence_topology"] == "TWO_PARTICIPANT_INTERACTION"
    assert record["supporting_trace_candidate_count"] == 2
    assert record["supporting_consequence_candidate_count"] == 2
    assert record["projection_is_causal_truth"] is False
    assert payload["legacy_trace_records_are_support_evidence_not_action_universe"] is True


def test_projection_count_mismatch_fails_closed() -> None:
    trace_payload = {
        "status": "REVIEW_REQUIRED",
        "current_occurrence_candidate_count": 2,
        "trackable_action_trace_candidate_count": 1,
        "occurrence_trace_binding_records": [
            {
                "action_occurrence_candidate_id": "aoc_1",
                "occurrence_topology": "SINGLE_ACTOR_ACTION",
                "required_participant_scope": "ACTOR_ONLY",
                "binding_state": "SINGLE_ACTOR_TRACE_VISIBLE_CANDIDATE",
            }
        ],
        "trackable_action_trace_candidates": [_trace("trace_1", "aoc_1", "actor_1", "team_1")],
    }
    consequence_payload = {
        "status": "REVIEW_REQUIRED",
        "trackable_action_consequence_candidate_count": 1,
        "trackable_action_consequence_candidates": [_consequence("cons_1", "aoc_1", "trace_1")],
    }

    payload = build_occurrence_consequence_projection(trace_payload, consequence_payload)

    assert payload["status"] == "FAIL_CLOSED"
    assert "occurrence_projection_count_mismatch" in payload["hard_block_hits"]
    assert payload["true_action_count"] == "UNKNOWN"
    assert payload["production_release"] is False


def test_occurrence_without_consequence_is_preserved_as_review_required() -> None:
    trace_payload = {
        "status": "REVIEW_REQUIRED",
        "current_occurrence_candidate_count": 1,
        "trackable_action_trace_candidate_count": 1,
        "occurrence_trace_binding_records": [
            {
                "action_occurrence_candidate_id": "aoc_1",
                "occurrence_topology": "SINGLE_ACTOR_ACTION",
                "required_participant_scope": "ACTOR_ONLY",
                "binding_state": "SINGLE_ACTOR_TRACE_VISIBLE_CANDIDATE",
            }
        ],
        "trackable_action_trace_candidates": [_trace("trace_1", "aoc_1", "actor_1", "team_1")],
    }
    consequence_payload = {
        "status": "REVIEW_REQUIRED",
        "trackable_action_consequence_candidate_count": 0,
        "trackable_action_consequence_candidates": [],
    }

    payload = build_occurrence_consequence_projection(trace_payload, consequence_payload)

    assert payload["occurrence_consequence_projection_count"] == 1
    assert payload["occurrence_without_consequence_record_count"] == 1
    assert payload["status"] == "REVIEW_REQUIRED"
    record = payload["occurrence_consequence_projections"][0]
    assert record["record_status"] == "REVIEW_REQUIRED"
    assert record["supporting_consequence_candidate_count"] == 0


def test_legacy_unbound_consequence_cannot_create_occurrence_member() -> None:
    bound_trace = _trace("trace_bound", "aoc_1", "actor_1", "team_1")
    legacy_trace = _trace("trace_legacy", "legacy_occ", "legacy_actor", "legacy_team")
    trace_payload = {
        "status": "REVIEW_REQUIRED",
        "current_occurrence_candidate_count": 1,
        "trackable_action_trace_candidate_count": 2,
        "primary_occurrence_trace_candidates": [bound_trace],
        "occurrence_trace_binding_records": [
            {
                "action_occurrence_candidate_id": "aoc_1",
                "occurrence_topology": "SINGLE_ACTOR_ACTION",
                "required_participant_scope": "ACTOR_ONLY",
                "binding_state": "SINGLE_ACTOR_TRACE_VISIBLE_CANDIDATE",
            }
        ],
        "trackable_action_trace_candidates": [bound_trace, legacy_trace],
    }
    consequence_payload = {
        "status": "REVIEW_REQUIRED",
        "trackable_action_consequence_candidate_count": 2,
        "trackable_action_consequence_candidates": [
            _consequence("cons_bound", "aoc_1", "trace_bound"),
            _consequence("cons_legacy", "legacy_occ", "trace_legacy"),
        ],
    }

    payload = build_occurrence_consequence_projection(trace_payload, consequence_payload)

    assert payload["source_trace_member_surface"] == "PRIMARY_OCCURRENCE_TRACE"
    assert payload["source_primary_occurrence_trace_candidate_count"] == 1
    assert payload["occurrence_consequence_projection_count"] == 1
    assert payload["occurrence_consequence_projections"][0]["action_occurrence_candidate_id"] == "aoc_1"
    assert payload["legacy_unbound_consequence_candidate_count"] == 1
    assert payload["occurrence_binding_records_are_primary_member_authority"] is True
    assert payload["legacy_consequence_records_cannot_create_occurrence_members"] is True


def _recovery_followup_case(*, follow_team: str = "team_1", follow_families=None, follow_labels=None, mixed: bool = False):
    anchor = _trace("trace_anchor", "aoc_anchor", "actor_1", "team_1")
    anchor["action_family_candidates"] = ["RECOVERY"]
    anchor["normalized_labels"] = ["ball recoveries"]
    follow = _trace("trace_follow", "aoc_follow", "actor_2", follow_team)
    follow["start_candidate"] = "11.0"
    follow["end_candidate"] = "13.0"
    follow["action_family_candidates"] = list(follow_families or ["PASS"])
    follow["normalized_labels"] = list(follow_labels or ["passes accurate"])
    traces = [anchor, follow]
    admitted = ["trace_follow"]
    visible = ["trace_follow"]
    primary = "RECOVERY_TO_SAME_TEAM_CONTINUATION_CANDIDATE"
    if mixed:
        other = _trace("trace_other", "aoc_other", "actor_3", "team_2")
        other["start_candidate"] = "11.0"
        other["end_candidate"] = "13.0"
        other["action_family_candidates"] = ["DUEL"]
        other["normalized_labels"] = ["duels"]
        traces.append(other)
        admitted.append("trace_other")
        visible.append("trace_other")
        primary = "MIXED_TEAM_SAME_TIME_FOLLOW_UP_REVIEW_REQUIRED_CANDIDATE"
    elif follow_team != "team_1":
        primary = "OPPONENT_HANDOVER_CANDIDATE"

    trace_payload = {
        "status": "REVIEW_REQUIRED",
        "current_occurrence_candidate_count": 1,
        "trackable_action_trace_candidate_count": len(traces),
        "occurrence_trace_binding_records": [
            {
                "action_occurrence_candidate_id": "aoc_anchor",
                "occurrence_topology": "SINGLE_ACTOR_ACTION",
                "required_participant_scope": "ACTOR_ONLY",
                "binding_state": "SINGLE_ACTOR_TRACE_VISIBLE_CANDIDATE",
            }
        ],
        "primary_occurrence_trace_candidates": [anchor],
        "trackable_action_trace_candidates": traces,
    }
    consequence_payload = {
        "status": "REVIEW_REQUIRED",
        "trackable_action_consequence_candidate_count": 1,
        "trackable_action_consequence_candidates": [
            {
                "trackable_action_consequence_candidate_id": "cons_anchor",
                "anchor_trackable_action_trace_candidate_id": "trace_anchor",
                "supporting_action_occurrence_candidate_ids": ["aoc_anchor"],
                "visible_follow_up_trace_ids": visible,
                "admitted_after_follow_up_trace_ids": admitted,
                "consequence_signal_candidates": [],
                "primary_consequence_candidate": primary,
                "terminal_outcome_support_visible": False,
                "derived_consequence_support_visible": False,
                "record_status": "REVIEW_REQUIRED" if mixed else "PASS_CANDIDATE_CLASSIFICATION",
            }
        ],
    }
    return trace_payload, consequence_payload


def test_recovery_first_admitted_followup_exposes_pass_semantics_without_control_promotion() -> None:
    trace_payload, consequence_payload = _recovery_followup_case(
        follow_families=["PASS"],
        follow_labels=["passes accurate", "passes forward accurate", "progressive passes accurate"],
    )
    payload = build_occurrence_consequence_projection(trace_payload, consequence_payload)
    row = payload["occurrence_consequence_projections"][0]
    assert row["recovery_first_admitted_followup_state"] == "CONTINUATION_ADMITTED"
    assert row["recovery_first_admitted_followup_action_family_candidates"] == ["PASS"]
    assert row["recovery_first_admitted_followup_provider_semantic_candidates"] == [
        "PROVIDER_ACCURATE_PASS_VISIBLE_CANDIDATE",
        "PROVIDER_FORWARD_PASS_VISIBLE_CANDIDATE",
        "PROVIDER_PROGRESSIVE_PASS_VISIBLE_CANDIDATE",
    ]
    assert row["recovery_first_admitted_followup_is_control_truth"] is False
    assert row["recovery_first_admitted_followup_is_progression_truth"] is False
    assert row["recovery_first_admitted_followup_is_causal_consequence_truth"] is False


def test_recovery_first_admitted_followup_can_expose_reloss_candidate() -> None:
    trace_payload, consequence_payload = _recovery_followup_case(
        follow_families=["PASS", "TURNOVER"],
        follow_labels=["passes inaccurate", "lost balls"],
    )
    payload = build_occurrence_consequence_projection(trace_payload, consequence_payload)
    row = payload["occurrence_consequence_projections"][0]
    assert row["recovery_first_admitted_followup_state"] == "RELOSS_VISIBLE_CANDIDATE"
    assert payload["recovery_first_admitted_followup_state_counts"] == {"RELOSS_VISIBLE_CANDIDATE": 1}


def test_recovery_first_admitted_followup_can_expose_opponent_continuation() -> None:
    trace_payload, consequence_payload = _recovery_followup_case(follow_team="team_2")
    payload = build_occurrence_consequence_projection(trace_payload, consequence_payload)
    row = payload["occurrence_consequence_projections"][0]
    assert row["recovery_first_admitted_followup_state"] == "OPPONENT_CONTINUATION_VISIBLE_CANDIDATE"
    assert row["recovery_first_admitted_followup_is_possession_truth"] is False


def test_recovery_first_mixed_team_layer_stays_order_unresolved() -> None:
    trace_payload, consequence_payload = _recovery_followup_case(mixed=True)
    payload = build_occurrence_consequence_projection(trace_payload, consequence_payload)
    row = payload["occurrence_consequence_projections"][0]
    assert row["recovery_first_admitted_followup_state"] == "ORDER_UNRESOLVED"
    assert row["recovery_first_admitted_followup_same_timestamp_internal_ordering_allowed"] is False


def test_inaccurate_pass_label_does_not_become_accurate_pass_provider_cue() -> None:
    trace_payload, consequence_payload = _recovery_followup_case(
        follow_families=["PASS"],
        follow_labels=["passes inaccurate", "incomplete passes forward"],
    )
    payload = build_occurrence_consequence_projection(trace_payload, consequence_payload)
    row = payload["occurrence_consequence_projections"][0]
    assert "PROVIDER_ACCURATE_PASS_VISIBLE_CANDIDATE" not in row[
        "recovery_first_admitted_followup_provider_semantic_candidates"
    ]
    assert "PROVIDER_FORWARD_PASS_VISIBLE_CANDIDATE" in row[
        "recovery_first_admitted_followup_provider_semantic_candidates"
    ]
