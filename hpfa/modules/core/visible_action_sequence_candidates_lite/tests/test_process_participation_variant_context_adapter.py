from __future__ import annotations

import json

from hpfa.modules.core.visible_action_sequence_candidates_lite.src.process_participation_variant_context_adapter import (
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
