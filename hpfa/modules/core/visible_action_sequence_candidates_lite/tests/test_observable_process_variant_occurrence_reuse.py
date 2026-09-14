from hpfa.modules.core.visible_action_sequence_candidates_lite.src.observable_process_variant_binding_projection import (
    build_observable_process_variant_binding,
)


def _sequence_payload():
    return {
        "partial_order_occurrence_variants": [
            {
                "partial_order_occurrence_variant_id": "v1",
                "team_identity_candidate_id": "team-1",
                "period_candidate": "1",
                "dependency_group_refs": ["dep-1", "dep-2"],
                "supporting_action_occurrence_candidate_ids": ["o1", "o2"],
            },
            {
                "partial_order_occurrence_variant_id": "v2",
                "team_identity_candidate_id": "team-1",
                "period_candidate": "1",
                "dependency_group_refs": ["dep-2", "dep-3"],
                "supporting_action_occurrence_candidate_ids": ["o2", "o3"],
            },
            {
                "partial_order_occurrence_variant_id": "v3",
                "team_identity_candidate_id": "team-1",
                "period_candidate": "1",
                "dependency_group_refs": ["dep-3", "dep-4"],
                "supporting_action_occurrence_candidate_ids": ["o3", "o4"],
            },
        ],
        "comparable_outcome_counterevidence_records": [
            {
                "partial_order_similarity_pair_ref": "p12",
                "comparison_eligible": True,
                "left_sequence_ref": "s1",
                "right_sequence_ref": "s2",
                "left_visible_outcome_state": "SUCCESS_SEMANTIC_VISIBLE",
                "right_visible_outcome_state": "SUCCESS_SEMANTIC_VISIBLE",
                "dependency_independence_proven": False,
                "statistical_independence_proven": False,
            },
            {
                "partial_order_similarity_pair_ref": "p23",
                "comparison_eligible": True,
                "left_sequence_ref": "s2",
                "right_sequence_ref": "s3",
                "left_visible_outcome_state": "SUCCESS_SEMANTIC_VISIBLE",
                "right_visible_outcome_state": "FAILURE_SEMANTIC_VISIBLE",
                "dependency_independence_proven": False,
                "statistical_independence_proven": False,
            },
        ],
    }


def _grammar_payload():
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
                "supported_sequence_grammar_alignment_id": "a12",
                "source_similarity_pair_ref": "p12",
                "left_variant_ref": "v1",
                "right_variant_ref": "v2",
                "grammar_edit_distance": 0.0,
                "grammar_edit_distance_normalized": 0.0,
                "left_layer_tokens": ["LAYER[PASS]", "LAYER[PASS]"],
                "right_layer_tokens": ["LAYER[PASS]", "LAYER[PASS]"],
                "supported_common_core_tokens": ["LAYER[PASS]", "LAYER[PASS]"],
                "first_supported_grammar_divergence": None,
            },
            {
                "supported_sequence_grammar_alignment_id": "a23",
                "source_similarity_pair_ref": "p23",
                "left_variant_ref": "v2",
                "right_variant_ref": "v3",
                "grammar_edit_distance": 0.0,
                "grammar_edit_distance_normalized": 0.0,
                "left_layer_tokens": ["LAYER[PASS]", "LAYER[PASS]"],
                "right_layer_tokens": ["LAYER[PASS]", "LAYER[PASS]"],
                "supported_common_core_tokens": ["LAYER[PASS]", "LAYER[PASS]"],
                "first_supported_grammar_divergence": None,
            },
        ],
    }


def test_occurrence_reuse_is_exposed_and_never_promoted_to_independent_recurrence():
    result = build_observable_process_variant_binding(_sequence_payload(), _grammar_payload())

    assert result["status"] == "PASS"
    assert result["observable_process_variant_family_count"] == 1
    assert result["occurrence_reuse_visible_family_count"] == 1
    assert result["member_count_is_independent_support_count"] is False
    assert result["unique_occurrence_count_is_independent_support_count"] is False

    family = result["observable_process_variant_families"][0]
    assert family["member_count"] == 3
    assert family["supporting_occurrence_slot_count"] == 6
    assert family["unique_supporting_action_occurrence_candidate_count"] == 4
    assert family["unique_supporting_action_occurrence_candidate_ids"] == ["o1", "o2", "o3", "o4"]
    assert family["supporting_occurrence_reuse_slot_count"] == 2
    assert family["supporting_occurrence_reuse_state"] == "OCCURRENCE_REUSE_VISIBLE"
    assert family["member_count_is_independent_support_count"] is False
    assert family["unique_occurrence_count_is_independent_support_count"] is False
    assert family["occurrence_reuse_is_recurrence_truth"] is False
    assert family["independent_recurrence_support_count"] == 0
    assert family["family_is_independent_recurrence_truth"] is False

    assert family["member_records"][0]["supporting_action_occurrence_candidate_count"] == 2
    assert family["member_records"][1]["supporting_action_occurrence_candidate_count"] == 2
    assert family["member_records"][2]["supporting_action_occurrence_candidate_count"] == 2


def test_non_overlapping_members_report_no_occurrence_reuse_without_creating_support_truth():
    sequence = _sequence_payload()
    sequence["partial_order_occurrence_variants"][1]["supporting_action_occurrence_candidate_ids"] = ["o5", "o6"]
    sequence["partial_order_occurrence_variants"][2]["supporting_action_occurrence_candidate_ids"] = ["o7", "o8"]

    result = build_observable_process_variant_binding(sequence, _grammar_payload())
    family = result["observable_process_variant_families"][0]

    assert family["supporting_occurrence_slot_count"] == 6
    assert family["unique_supporting_action_occurrence_candidate_count"] == 6
    assert family["supporting_occurrence_reuse_slot_count"] == 0
    assert family["supporting_occurrence_reuse_state"] == "NO_OCCURRENCE_REUSE_VISIBLE"
    assert family["independent_recurrence_support_count"] == 0
    assert family["family_is_independent_recurrence_truth"] is False
