from __future__ import annotations

import json

from hpfa.modules.core.visible_action_sequence_candidates_lite.src.observable_process_variant_binding_projection import (
    build_observable_process_variant_binding,
)


def _variant(variant_id: str, sequence_ref: str, *, team: str = "team_a", period: str = "2") -> dict:
    return {
        "partial_order_occurrence_variant_id": variant_id,
        "sequence_ref": sequence_ref,
        "team_identity_candidate_id": team,
        "period_candidate": period,
        "dependency_group_refs": [f"dep:{variant_id}"],
    }


def _sequence_payload(*, same_outcome: bool = False) -> dict:
    right_outcome = "SUCCESS_SEMANTIC_VISIBLE" if same_outcome else "FAILURE_SEMANTIC_VISIBLE"
    return {
        "partial_order_occurrence_variants": [
            _variant("v1", "s1"),
            _variant("v2", "s2"),
        ],
        "comparable_outcome_counterevidence_records": [
            {
                "partial_order_similarity_pair_ref": "pair_1",
                "comparable_outcome_counterevidence_id": "coc_1",
                "comparison_eligible": True,
                "comparison_eligibility_state": "COMPARABLE_FOR_SHARED_ORIGIN_BRANCH_CONTRAST",
                "left_variant_ref": "v1",
                "right_variant_ref": "v2",
                "left_sequence_ref": "s1",
                "right_sequence_ref": "s2",
                "left_visible_outcome_state": "SUCCESS_SEMANTIC_VISIBLE",
                "right_visible_outcome_state": right_outcome,
                "dependency_independence_proven": False,
                "statistical_independence_proven": False,
            }
        ],
    }


def _grammar_payload(*, distance: float = 0.0, outcome_excluded: bool = True) -> dict:
    return {
        "status": "PASS",
        "supported_sequence_grammar_alignments": [
            {
                "supported_sequence_grammar_alignment_id": "ga_1",
                "source_similarity_pair_ref": "pair_1",
                "left_variant_ref": "v1",
                "right_variant_ref": "v2",
                "left_layer_tokens": ["LAYER[PASS|PASS]", "LAYER[PASS]"],
                "right_layer_tokens": ["LAYER[PASS|PASS]", "LAYER[PASS]"],
                "supported_common_core_tokens": ["LAYER[PASS|PASS]", "LAYER[PASS]"],
                "grammar_edit_distance": distance,
                "grammar_edit_distance_normalized": distance / 2 if distance else 0.0,
                "first_supported_grammar_divergence": None if distance == 0.0 else {"operation": "SUBSTITUTE"},
            }
        ],
        "outcome_excluded_from_alignment": outcome_excluded,
        "same_timestamp_internal_ordering_allowed": False,
        "source_row_order_is_temporal_truth": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def test_exact_grammar_different_outcome_forms_visible_variation_family() -> None:
    result = build_observable_process_variant_binding(_sequence_payload(), _grammar_payload())
    assert result["status"] == "PASS"
    assert result["observable_process_variant_binding_count"] == 1
    assert result["observable_process_variant_family_count"] == 1
    assert result["grammar_stable_visible_outcome_variation_family_count"] == 1
    binding = result["observable_process_variant_bindings"][0]
    assert binding["process_variant_state"] == "GRAMMAR_STABLE_DIFFERENT_VISIBLE_OUTCOME_VARIANT"
    assert binding["same_grammar_different_visible_outcome_candidate"] is True
    assert binding["current_action_family_grammar_discriminates_visible_outcome"] is False
    family = result["observable_process_variant_families"][0]
    assert family["process_variant_family_state"] == "GRAMMAR_STABLE_VISIBLE_OUTCOME_VARIATION"
    assert family["same_grammar_visible_outcome_variation_observed"] is True
    assert family["visible_outcome_state_counts"] == {
        "FAILURE_SEMANTIC_VISIBLE": 1,
        "SUCCESS_SEMANTIC_VISIBLE": 1,
    }


def test_same_grammar_same_outcome_is_not_outcome_variation() -> None:
    result = build_observable_process_variant_binding(
        _sequence_payload(same_outcome=True),
        _grammar_payload(),
    )
    family = result["observable_process_variant_families"][0]
    assert family["process_variant_family_state"] == "GRAMMAR_STABLE_SINGLE_VISIBLE_OUTCOME"
    assert family["same_grammar_visible_outcome_variation_observed"] is False
    assert family["current_action_family_grammar_discriminates_visible_outcome"] is None


def test_grammar_divergence_does_not_create_exact_grammar_family() -> None:
    result = build_observable_process_variant_binding(
        _sequence_payload(),
        _grammar_payload(distance=0.5),
    )
    binding = result["observable_process_variant_bindings"][0]
    assert binding["process_variant_state"] == "GRAMMAR_DIVERGENT_DIFFERENT_VISIBLE_OUTCOME_VARIANT"
    assert binding["same_grammar_different_visible_outcome_candidate"] is False
    assert result["observable_process_variant_family_count"] == 0


def test_outcome_alignment_leakage_fails_closed() -> None:
    result = build_observable_process_variant_binding(
        _sequence_payload(),
        _grammar_payload(outcome_excluded=False),
    )
    assert result["status"] == "FAIL_CLOSED"
    assert result["observable_process_variant_binding_count"] == 0
    assert "grammar_alignment_outcome_exclusion_missing" in result["hard_block_hits"]


def test_dependency_does_not_become_recurrence_or_causality() -> None:
    result = build_observable_process_variant_binding(_sequence_payload(), _grammar_payload())
    binding = result["observable_process_variant_bindings"][0]
    family = result["observable_process_variant_families"][0]
    assert binding["dependency_independence_proven"] is False
    assert binding["statistical_independence_proven"] is False
    assert binding["process_variant_binding_is_causal_explanation"] is False
    assert family["independent_recurrence_support_count"] == 0
    assert family["family_is_independent_recurrence_truth"] is False
    assert family["family_is_tactical_pattern_truth"] is False
    assert family["family_is_causal_mechanism_truth"] is False


def test_truth_and_release_locks_remain_closed() -> None:
    result = build_observable_process_variant_binding(_sequence_payload(), _grammar_payload())
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["true_action_count"] == "UNKNOWN"
    assert result["production_release"] is False
    assert result["process_variant_family_is_recurrence_truth"] is False
    assert result["process_variant_family_is_tactical_pattern_truth"] is False
    assert result["process_variant_family_is_causal_mechanism_truth"] is False


def test_no_sample_match_identity_leak() -> None:
    result = build_observable_process_variant_binding(_sequence_payload(), _grammar_payload())
    rendered = json.dumps(result, ensure_ascii=False).casefold()
    for forbidden in ("sporting", "roma", "fenerbah", "galatasaray"):
        assert forbidden not in rendered
