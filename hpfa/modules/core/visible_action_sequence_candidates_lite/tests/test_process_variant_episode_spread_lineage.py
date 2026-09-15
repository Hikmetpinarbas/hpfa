from hpfa.modules.core.visible_action_sequence_candidates_lite.src.observable_process_variant_binding_projection import (
    build_observable_process_variant_binding,
)
from hpfa.modules.core.visible_action_sequence_candidates_lite.src.process_participation_variant_context_adapter import (
    apply_process_context_to_comparison,
)


def _sequence() -> dict:
    return {
        "partial_order_occurrence_variants": [
            {
                "partial_order_occurrence_variant_id": "v1",
                "team_identity_candidate_id": "team_a",
                "period_candidate": "1",
                "dependency_group_refs": ["dep_1"],
                "supporting_action_occurrence_candidate_ids": ["o1", "o2"],
                "node_records": [{"time_layer_ref": "l1", "occurrence_refs": ["o1", "o2"]}],
            },
            {
                "partial_order_occurrence_variant_id": "v2",
                "team_identity_candidate_id": "team_a",
                "period_candidate": "1",
                "dependency_group_refs": ["dep_2"],
                "supporting_action_occurrence_candidate_ids": ["o3", "o4"],
                "node_records": [{"time_layer_ref": "l2", "occurrence_refs": ["o3", "o4"]}],
            },
        ],
        "dependency_aware_partial_order_similarity_pairs": [
            {
                "partial_order_similarity_pair_id": "pair_1",
                "left_variant_ref": "v1",
                "right_variant_ref": "v2",
                "comparison_eligible": True,
                "comparison_outcome_contrast_allowed": True,
                "recurrence_candidate_eligible": True,
                "comparison_requires_review": False,
                "outcome_used_in_similarity_decision": False,
            }
        ],
        "dependency_aware_partial_order_similarity_pair_count": 1,
        "comparison_eligible_pair_count": 1,
        "recurrence_candidate_eligible_pair_count": 1,
        "comparable_outcome_counterevidence_records": [
            {
                "partial_order_similarity_pair_ref": "pair_1",
                "comparison_eligible": True,
                "left_sequence_ref": "s1",
                "right_sequence_ref": "s2",
                "left_visible_outcome_state": "SUCCESS_SEMANTIC_VISIBLE",
                "right_visible_outcome_state": "FAILURE_SEMANTIC_VISIBLE",
                "dependency_independence_proven": False,
                "statistical_independence_proven": False,
            }
        ],
        "same_timestamp_internal_ordering_allowed": False,
        "source_row_order_is_temporal_truth": False,
        "outcome_used_in_similarity_decision": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _occurrences() -> dict:
    return {
        "status": "PASS",
        "occurrence_consequence_projections": [
            {
                "action_occurrence_candidate_id": "o1",
                "team_identity_candidate_ids": ["team_a"],
                "period_candidates": ["1"],
                "start_candidates": [10.0],
                "end_candidates": [11.0],
            },
            {
                "action_occurrence_candidate_id": "o2",
                "team_identity_candidate_ids": ["team_a"],
                "period_candidates": ["1"],
                "start_candidates": [12.0],
                "end_candidates": [13.0],
            },
            {
                "action_occurrence_candidate_id": "o3",
                "team_identity_candidate_ids": ["team_a"],
                "period_candidates": ["1"],
                "start_candidates": [50.0],
                "end_candidates": [51.0],
            },
            {
                "action_occurrence_candidate_id": "o4",
                "team_identity_candidate_ids": ["team_a"],
                "period_candidates": ["1"],
                "start_candidates": [52.0],
                "end_candidates": [53.0],
            },
        ],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _process(*, second_episode: str = "episode_2") -> dict:
    return {
        "status": "PASS",
        "process_participation_candidates": [
            {
                "semantic_role": "CONTEXT_INTERVAL",
                "process_family_candidate": "POSITIONAL_ATTACK_CANDIDATE",
                "team_identity_candidate_id": "team_a",
                "period_candidate": "1",
                "start_candidate": 9.0,
                "end_candidate": 14.0,
                "episode_candidate_id": "episode_1",
            },
            {
                "semantic_role": "CONTEXT_INTERVAL",
                "process_family_candidate": "POSITIONAL_ATTACK_CANDIDATE",
                "team_identity_candidate_id": "team_a",
                "period_candidate": "1",
                "start_candidate": 49.0,
                "end_candidate": 54.0,
                "episode_candidate_id": second_episode,
            },
        ],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _grammar() -> dict:
    return {
        "status": "PASS",
        "outcome_excluded_from_alignment": True,
        "same_timestamp_internal_ordering_allowed": False,
        "source_row_order_is_temporal_truth": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "supported_sequence_grammar_alignments": [
            {
                "supported_sequence_grammar_alignment_id": "align_1",
                "source_similarity_pair_ref": "pair_1",
                "left_variant_ref": "v1",
                "right_variant_ref": "v2",
                "grammar_edit_distance": 0.0,
                "grammar_edit_distance_normalized": 0.0,
                "left_layer_tokens": ["LAYER[PASS]", "LAYER[PASS]"],
                "right_layer_tokens": ["LAYER[PASS]", "LAYER[PASS]"],
                "supported_common_core_tokens": ["LAYER[PASS]", "LAYER[PASS]"],
                "first_supported_grammar_divergence": None,
            }
        ],
    }


def test_episode_navigation_is_descriptive_lineage_not_comparison_admission() -> None:
    enriched = apply_process_context_to_comparison(_sequence(), _process(), _occurrences())

    pair = enriched["dependency_aware_partial_order_similarity_pairs"][0]
    assert pair["comparison_eligible"] is True
    assert pair["comparison_process_context_state"] == "MATCHED_PROVIDER_REVIEWED_TEAM_PROCESS_CONTEXT"
    assert pair["left_process_context_episode_candidate_ids"] == ["episode_1"]
    assert pair["right_process_context_episode_candidate_ids"] == ["episode_2"]
    assert pair["process_context_episode_navigation_used_in_admission"] is False
    assert pair["process_context_episode_navigation_is_admission_dimension"] is False
    assert pair["process_context_episode_spread_is_independent_support"] is False
    assert pair["process_context_episode_spread_is_recurrence_truth"] is False
    assert enriched["process_comparison_episode_navigation_is_admission_dimension"] is False
    assert enriched["episode_navigation_binding_is_possession_truth"] is False


def test_process_variant_family_exposes_multi_episode_spread_without_recurrence_promotion() -> None:
    enriched = apply_process_context_to_comparison(_sequence(), _process(), _occurrences())
    result = build_observable_process_variant_binding(enriched, _grammar())

    assert result["observable_process_variant_family_count"] == 1
    assert result["multi_visible_episode_spread_family_count"] == 1
    assert result["episode_spread_count_is_independent_support_count"] is False
    assert result["episode_spread_is_recurrence_truth"] is False

    family = result["observable_process_variant_families"][0]
    assert family["visible_episode_candidate_ids"] == ["episode_1", "episode_2"]
    assert family["visible_episode_spread_count"] == 2
    assert family["visible_episode_spread_state"] == "MULTIPLE_VISIBLE_EPISODE_CANDIDATES"
    assert family["success_visible_episode_candidate_ids"] == ["episode_1"]
    assert family["failure_visible_episode_candidate_ids"] == ["episode_2"]
    assert family["success_visible_episode_spread_count"] == 1
    assert family["failure_visible_episode_spread_count"] == 1
    assert family["episode_navigation_binding_is_possession_truth"] is False
    assert family["episode_spread_count_is_independent_support_count"] is False
    assert family["episode_spread_is_recurrence_truth"] is False
    assert family["independent_recurrence_support_count"] == 0
    assert family["family_is_independent_recurrence_truth"] is False
    assert family["family_is_tactical_pattern_truth"] is False


def test_single_episode_concentration_does_not_become_recurrence_truth() -> None:
    enriched = apply_process_context_to_comparison(
        _sequence(), _process(second_episode="episode_1"), _occurrences()
    )
    result = build_observable_process_variant_binding(enriched, _grammar())
    family = result["observable_process_variant_families"][0]

    assert result["multi_visible_episode_spread_family_count"] == 0
    assert family["visible_episode_candidate_ids"] == ["episode_1"]
    assert family["visible_episode_spread_count"] == 1
    assert family["visible_episode_spread_state"] == "SINGLE_VISIBLE_EPISODE_CONCENTRATION"
    assert family["episode_spread_is_recurrence_truth"] is False
    assert family["independent_recurrence_support_count"] == 0
