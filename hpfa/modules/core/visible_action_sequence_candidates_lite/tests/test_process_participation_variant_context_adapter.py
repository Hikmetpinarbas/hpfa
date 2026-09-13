from __future__ import annotations

import json

from hpfa.modules.core.visible_action_sequence_candidates_lite.src.process_participation_variant_context_adapter import (
    apply_process_context_to_comparison,
    apply_process_participation_context,
)


def _sequence() -> dict:
    return {
        "partial_order_occurrence_variants": [
            {
                "partial_order_occurrence_variant_id": "v_success",
                "node_records": [
                    {"time_layer_ref": "s0", "occurrence_refs": ["o_success"]},
                ],
            },
            {
                "partial_order_occurrence_variant_id": "v_failure",
                "node_records": [
                    {"time_layer_ref": "f0", "occurrence_refs": ["o_failure"]},
                ],
            },
        ],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _comparison_sequence() -> dict:
    return {
        "partial_order_occurrence_variants": [
            {
                "partial_order_occurrence_variant_id": "v_left",
                "team_identity_candidate_id": "team_a",
                "period_candidate": "1",
                "supporting_action_occurrence_candidate_ids": ["o_left"],
                "node_records": [{"time_layer_ref": "l0", "occurrence_refs": ["o_left"]}],
            },
            {
                "partial_order_occurrence_variant_id": "v_right",
                "team_identity_candidate_id": "team_a",
                "period_candidate": "1",
                "supporting_action_occurrence_candidate_ids": ["o_right"],
                "node_records": [{"time_layer_ref": "r0", "occurrence_refs": ["o_right"]}],
            },
        ],
        "dependency_aware_partial_order_similarity_pairs": [
            {
                "partial_order_similarity_pair_id": "pair_1",
                "left_variant_ref": "v_left",
                "right_variant_ref": "v_right",
                "comparison_eligible": True,
                "comparison_outcome_contrast_allowed": True,
                "recurrence_candidate_eligible": True,
                "comparison_requires_review": False,
            }
        ],
        "dependency_aware_partial_order_similarity_pair_count": 1,
        "comparison_eligible_pair_count": 1,
        "recurrence_candidate_eligible_pair_count": 1,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _feature_delta() -> dict:
    return {
        "status": "REVIEW_REQUIRED",
        "grammar_stable_variant_feature_delta_records": [
            {
                "grammar_stable_variant_feature_delta_id": "d1",
                "source_process_variant_family_ref": "fam_1",
                "context_feature_difference_candidates": [],
                "context_feature_difference_candidate_count": 0,
                "first_supported_context_difference_layer_candidate": None,
                "member_profiles": [
                    {
                        "variant_ref": "v_success",
                        "visible_outcome_state": "SUCCESS_SEMANTIC_VISIBLE",
                        "supporting_occurrence_refs": ["o_success"],
                    },
                    {
                        "variant_ref": "v_failure",
                        "visible_outcome_state": "FAILURE_SEMANTIC_VISIBLE",
                        "supporting_occurrence_refs": ["o_failure"],
                    },
                ],
            }
        ],
        "review_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _occurrences() -> dict:
    return {
        "status": "PASS",
        "occurrence_consequence_projections": [
            {
                "action_occurrence_candidate_id": "o_success",
                "actor_identity_candidate_ids": ["actor_a"],
                "team_identity_candidate_ids": ["team_a"],
                "period_candidates": ["1"],
                "start_candidates": [10.0],
                "end_candidates": [11.0],
            },
            {
                "action_occurrence_candidate_id": "o_failure",
                "actor_identity_candidate_ids": ["actor_b"],
                "team_identity_candidate_ids": ["team_a"],
                "period_candidates": ["1"],
                "start_candidates": [20.0],
                "end_candidates": [21.0],
            },
            {
                "action_occurrence_candidate_id": "o_left",
                "actor_identity_candidate_ids": ["actor_a"],
                "team_identity_candidate_ids": ["team_a"],
                "period_candidates": ["1"],
                "start_candidates": [30.0],
                "end_candidates": [31.0],
            },
            {
                "action_occurrence_candidate_id": "o_right",
                "actor_identity_candidate_ids": ["actor_b"],
                "team_identity_candidate_ids": ["team_a"],
                "period_candidates": ["1"],
                "start_candidates": [40.0],
                "end_candidates": [41.0],
            },
        ],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _process() -> dict:
    return {
        "status": "PASS",
        "process_participation_candidates": [
            {
                "semantic_role": "PARTICIPATION_INTERVAL",
                "process_family_candidate": "POSITIONAL_ATTACK_CANDIDATE",
                "actor_identity_candidate_id": "actor_a",
                "team_identity_candidate_id": "team_a",
                "period_candidate": "1",
                "start_candidate": 9.0,
                "end_candidate": 12.0,
                "episode_candidate_id": "episode_1",
                "shot_present_annotation_candidate": False,
            },
            {
                "semantic_role": "PARTICIPATION_INTERVAL",
                "process_family_candidate": "COUNTERATTACK_CANDIDATE",
                "actor_identity_candidate_id": "actor_b",
                "team_identity_candidate_id": "team_a",
                "period_candidate": "1",
                "start_candidate": 19.0,
                "end_candidate": 22.0,
                "episode_candidate_id": "episode_2",
                "shot_present_annotation_candidate": True,
            },
        ],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _team_context_process(left_family: str | None, right_family: str | None) -> dict:
    rows = []
    if left_family:
        rows.append({
            "semantic_role": "CONTEXT_INTERVAL",
            "process_family_candidate": left_family,
            "team_identity_candidate_id": "team_a",
            "period_candidate": "1",
            "start_candidate": 29.0,
            "end_candidate": 32.0,
            "episode_candidate_id": "episode_left",
            "shot_present_annotation_candidate": True,
        })
    if right_family:
        rows.append({
            "semantic_role": "CONTEXT_INTERVAL",
            "process_family_candidate": right_family,
            "team_identity_candidate_id": "team_a",
            "period_candidate": "1",
            "start_candidate": 39.0,
            "end_candidate": 42.0,
            "episode_candidate_id": "episode_right",
            "shot_present_annotation_candidate": False,
        })
    return {
        "status": "PASS",
        "process_participation_candidates": rows,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def test_process_context_adds_incremental_variant_discrimination_without_causal_promotion() -> None:
    result = apply_process_participation_context(
        _sequence(), _feature_delta(), _process(), _occurrences()
    )
    assert result["process_participation_context_enrichment_consumed"] is True
    assert result["process_context_enriched_family_count"] == 1
    row = result["grammar_stable_variant_feature_delta_records"][0]
    features = {
        item["feature_token"]: item
        for item in row["process_context_feature_difference_candidates"]
    }
    assert "process_family_candidate:POSITIONAL_ATTACK_CANDIDATE" in features
    assert "process_family_candidate:COUNTERATTACK_CANDIDATE" in features
    assert "LAYER[0]::process_shot_present_annotation_candidate:TRUE" in features
    assert row["first_supported_process_context_difference_layer_candidate"] == 0
    assert row["process_annotation_is_tactical_plan_truth"] is False
    assert row["temporal_overlap_is_causal_truth"] is False
    assert result["process_context_rows_are_independent_evidence_votes"] is False


def test_unannotated_variant_is_not_used_as_negative_process_evidence() -> None:
    process = _process()
    process["process_participation_candidates"] = process["process_participation_candidates"][:1]
    result = apply_process_participation_context(
        _sequence(), _feature_delta(), process, _occurrences()
    )
    row = result["grammar_stable_variant_feature_delta_records"][0]
    assert row["process_context_success_eligible_variant_count"] == 1
    assert row["process_context_failure_eligible_variant_count"] == 0
    assert row["process_context_feature_difference_candidate_count"] == 0
    assert row["process_context_coverage_incomplete_variant_count"] == 1
    assert row["process_context_absence_is_counterevidence"] is False


def test_team_context_interval_can_bind_without_inventing_off_ball_or_possession_truth() -> None:
    process = _process()
    process["process_participation_candidates"] = [
        {
            "semantic_role": "CONTEXT_INTERVAL",
            "process_family_candidate": "POSITIONAL_ATTACK_CANDIDATE",
            "team_identity_candidate_id": "team_a",
            "period_candidate": "1",
            "start_candidate": 9.0,
            "end_candidate": 12.0,
            "episode_candidate_id": "episode_1",
            "shot_present_annotation_candidate": False,
        },
        {
            "semantic_role": "CONTEXT_INTERVAL",
            "process_family_candidate": "COUNTERATTACK_CANDIDATE",
            "team_identity_candidate_id": "team_a",
            "period_candidate": "1",
            "start_candidate": 19.0,
            "end_candidate": 22.0,
            "episode_candidate_id": "episode_2",
            "shot_present_annotation_candidate": False,
        },
    ]
    result = apply_process_participation_context(
        _sequence(), _feature_delta(), process, _occurrences()
    )
    rendered = json.dumps(result, ensure_ascii=False)
    assert "process_semantic_role:CONTEXT_INTERVAL" in rendered
    assert result["episode_navigation_binding_is_possession_truth"] is False
    assert result["process_annotation_is_tactical_plan_truth"] is False


def test_same_period_same_structure_known_process_context_mismatch_is_not_fully_comparable() -> None:
    result = apply_process_context_to_comparison(
        _comparison_sequence(),
        _team_context_process("POSITIONAL_ATTACK_CANDIDATE", "COUNTERATTACK_CANDIDATE"),
        _occurrences(),
    )
    pair = result["dependency_aware_partial_order_similarity_pairs"][0]
    assert result["process_comparison_context_consumed"] is True
    assert pair["comparison_eligible_before_process_context"] is True
    assert pair["comparison_eligible"] is False
    assert pair["comparison_outcome_contrast_allowed"] is False
    assert pair["recurrence_candidate_eligible"] is False
    assert pair["comparison_requires_review"] is True
    assert pair["comparison_process_context_state"] == "DIFFERENT_PROVIDER_REVIEWED_TEAM_PROCESS_CONTEXT"
    assert pair["comparison_process_context_match"] is False
    assert pair["process_context_outcome_used_in_admission"] is False
    assert pair["process_context_shot_annotation_used_in_admission"] is False
    assert pair["process_context_episode_navigation_used_in_admission"] is False
    assert result["process_comparison_context_lowered_pair_count"] == 1
    assert result["process_comparison_context_can_create_new_pair"] is False


def test_unknown_context_is_review_required_not_different_context_truth() -> None:
    result = apply_process_context_to_comparison(
        _comparison_sequence(),
        _team_context_process("POSITIONAL_ATTACK_CANDIDATE", None),
        _occurrences(),
    )
    pair = result["dependency_aware_partial_order_similarity_pairs"][0]
    assert pair["comparison_eligible"] is False
    assert pair["comparison_process_context_state"] == "UNKNOWN_PROVIDER_REVIEWED_TEAM_PROCESS_CONTEXT_REVIEW_REQUIRED"
    assert pair["comparison_process_context_match"] is None
    assert pair["unknown_context_is_different_context"] is False
    assert result["unknown_context_is_different_context"] is False


def test_matched_team_process_context_preserves_but_never_creates_eligibility() -> None:
    sequence = _comparison_sequence()
    result = apply_process_context_to_comparison(
        sequence,
        _team_context_process("POSITIONAL_ATTACK_CANDIDATE", "POSITIONAL_ATTACK_CANDIDATE"),
        _occurrences(),
    )
    pair = result["dependency_aware_partial_order_similarity_pairs"][0]
    assert pair["comparison_process_context_state"] == "MATCHED_PROVIDER_REVIEWED_TEAM_PROCESS_CONTEXT"
    assert pair["comparison_eligible"] is True
    assert result["process_comparison_context_lowered_pair_count"] == 0

    sequence = _comparison_sequence()
    sequence["dependency_aware_partial_order_similarity_pairs"][0]["comparison_eligible"] = False
    sequence["dependency_aware_partial_order_similarity_pairs"][0]["comparison_outcome_contrast_allowed"] = False
    sequence["dependency_aware_partial_order_similarity_pairs"][0]["recurrence_candidate_eligible"] = False
    result = apply_process_context_to_comparison(
        sequence,
        _team_context_process("POSITIONAL_ATTACK_CANDIDATE", "POSITIONAL_ATTACK_CANDIDATE"),
        _occurrences(),
    )
    pair = result["dependency_aware_partial_order_similarity_pairs"][0]
    assert pair["comparison_eligible"] is False
    assert pair["comparison_outcome_contrast_allowed"] is False
    assert pair["recurrence_candidate_eligible"] is False


def test_truth_lock_breach_keeps_original_feature_surface_and_refuses_process_consumption() -> None:
    process = _process()
    process["canonical_event_count"] = 2
    original = _feature_delta()
    result = apply_process_participation_context(
        _sequence(), original, process, _occurrences()
    )
    assert result["process_participation_context_enrichment_consumed"] is False
    assert result["process_participation_context_binding_state"] == "REVIEW_REQUIRED_NOT_CONSUMED"
    assert result["grammar_stable_variant_feature_delta_records"][0][
        "context_feature_difference_candidate_count"
    ] == 0


def test_no_sample_match_identity_leak() -> None:
    result = apply_process_participation_context(
        _sequence(), _feature_delta(), _process(), _occurrences()
    )
    rendered = json.dumps(result, ensure_ascii=False).casefold()
    for forbidden in ("sporting", "roma", "fenerbah", "galatasaray"):
        assert forbidden not in rendered
