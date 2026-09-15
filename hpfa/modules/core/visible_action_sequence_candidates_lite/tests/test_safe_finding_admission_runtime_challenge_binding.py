from __future__ import annotations

import json
from pathlib import Path

import safe_finding_admission_current_v1 as runtime


def _sequence_payload() -> dict:
    return {
        "comparable_outcome_counterevidence_status": "PASS",
        "safe_finding_handoff_candidates": [
            {
                "safe_finding_handoff_candidate_id": "sfh_1",
                "professional_finding_emit_allowed": False,
                "safe_finding_handoff_is_professional_finding_truth": False,
                "safe_finding_handoff_is_tactical_truth": False,
                "safe_finding_handoff_is_causal_truth": False,
                "safe_finding_handoff_is_coach_intention_truth": False,
                "same_timestamp_internal_ordering_allowed": False,
                "source_row_order_is_temporal_truth": False,
                "support": {
                    "visible_success_sequence_refs": ["s1"],
                    "admitted_independent_support_count": 1,
                    "dependency_independence_proven": True,
                    "statistical_independence_proven": True,
                },
                "counterevidence": {
                    "visible_failure_sequence_refs": ["s2"],
                    "comparable_counterexample_refs": ["counter_1"],
                },
                "evidence_sufficiency": {
                    "state": "NO_BLOCKING_DIMENSION_VISIBLE_BUT_EMIT_NOT_AUTHORIZED_HERE",
                    "blocking_dimensions": [],
                },
                "alternative_explanations": [
                    {"code": "ALT", "meaning": "visible alternative explanation"}
                ],
                "safe_meaning": "MATCH_LOCAL_VISIBLE_VARIATION_ONLY",
                "forbidden_inference": ["CAUSALITY", "COACH_INTENTION"],
                "withdrawal_conditions": ["WITHDRAW_IF_BINDING_INVALIDATED"],
            }
        ],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _feature_delta() -> dict:
    return {
        "status": "REVIEW_REQUIRED",
        "outcome_used_only_as_partition_label": True,
        "outcome_used_to_define_features": False,
        "feature_absence_is_counterevidence": False,
        "grammar_stable_variant_feature_delta_records": [
            {
                "grammar_stable_variant_feature_delta_id": "delta_1",
                "source_process_variant_family_ref": "family_1",
                "context_coverage_incomplete_variant_count": 0,
                "consequence_coverage_incomplete_variant_count": 0,
                "context_feature_difference_candidates": [
                    {
                        "feature_token": "provider_direction_candidates:FORWARD",
                        "success_visible_numerator": 1,
                        "success_eligible_denominator": 1,
                        "failure_visible_numerator": 0,
                        "failure_eligible_denominator": 1,
                        "descriptive_rate_delta_success_minus_failure": 1.0,
                        "dependency_independence_proven": False,
                        "statistical_independence_proven": False,
                    }
                ],
                "consequence_feature_difference_candidates": [],
            }
        ],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _process_variant() -> dict:
    return {
        "status": "REVIEW_REQUIRED",
        "observable_process_variant_families": [
            {
                "observable_process_variant_family_id": "family_1",
                "same_grammar_visible_outcome_variation_observed": True,
                "team_identity_candidate_ids": ["team_1"],
                "period_candidates": ["1"],
                "dependency_group_ref_count": 1,
                "dependency_group_refs": ["dep_1"],
                "family_is_independent_recurrence_truth": False,
                "member_records": [
                    {
                        "variant_ref": "v1",
                        "sequence_ref": "s1",
                        "visible_outcome_state": "SUCCESS_SEMANTIC_VISIBLE",
                    },
                    {
                        "variant_ref": "v2",
                        "sequence_ref": "s2",
                        "visible_outcome_state": "FAILURE_SEMANTIC_VISIBLE",
                    },
                ],
            }
        ],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def test_runtime_materializes_challenge_and_only_lowers_claim_ceiling(tmp_path: Path) -> None:
    sequence_path = tmp_path / "visible_action_sequence_candidates_lite_v1.json"
    sequence_path.write_text(json.dumps(_sequence_payload()), encoding="utf-8")
    (tmp_path / runtime.FEATURE_DELTA_NAME).write_text(
        json.dumps(_feature_delta()), encoding="utf-8"
    )
    (tmp_path / runtime.PROCESS_VARIANT_NAME).write_text(
        json.dumps(_process_variant()), encoding="utf-8"
    )

    result = runtime.runtime_write_outputs(sequence_path, tmp_path)

    assert result["variant_feature_challenge_materialized"] is True
    assert result["variant_feature_challenge_consumed"] is True
    assert (tmp_path / runtime.CHALLENGE_NAME).is_file()
    assert result["finding_status_counts"] == {
        "EMIT": 0,
        "DOWNGRADE": 1,
        "ABSTAIN": 0,
    }
    decision = result["safe_finding_admission_decisions"][0]
    assert decision["admitted_independent_support_count"] == 1
    assert decision["decision"] == "DOWNGRADE"
    assert decision["claim_output_allowed"] is False
    assert decision["variant_feature_challenge_refs"]
    assert result["variant_feature_challenge_can_increase_support"] is False
    assert result["variant_feature_challenge_can_authorize_emit"] is False
