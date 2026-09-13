from __future__ import annotations

from hpfa.modules.core.visible_action_sequence_candidates_lite.src.grammar_stable_variant_feature_delta_projection import (
    build_grammar_stable_variant_feature_delta,
)
from hpfa.modules.core.visible_action_sequence_candidates_lite.src.safe_finding_variant_feature_challenge_adapter import (
    apply_variant_feature_challenge_to_admission,
)
from hpfa.modules.core.visible_action_sequence_candidates_lite.src.variant_feature_challenge_projection import (
    build_variant_feature_challenge_projection,
)


def _sequence_variants() -> dict:
    return {
        "partial_order_occurrence_variants": [
            {
                "partial_order_occurrence_variant_id": "v_success",
                "time_layer_refs": ["s0"],
                "node_records": [{"time_layer_ref": "s0", "occurrence_refs": ["o_success"]}],
            },
            {
                "partial_order_occurrence_variant_id": "v_failure",
                "time_layer_refs": ["f0"],
                "node_records": [{"time_layer_ref": "f0", "occurrence_refs": ["o_failure"]}],
            },
        ],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _process_variants() -> dict:
    return {
        "status": "PASS",
        "grammar_stable_visible_outcome_variation_family_count": 1,
        "observable_process_variant_families": [
            {
                "observable_process_variant_family_id": "family_1",
                "same_grammar_visible_outcome_variation_observed": True,
                "grammar_signature_tokens": ["LAYER[PASS]"],
                "team_identity_candidate_ids": ["team_a"],
                "period_candidates": ["1"],
                "dependency_group_ref_count": 2,
                "dependency_group_refs": ["dep_1", "dep_2"],
                "family_is_independent_recurrence_truth": True,
                "member_records": [
                    {
                        "variant_ref": "v_success",
                        "sequence_ref": "s1",
                        "visible_outcome_state": "SUCCESS_SEMANTIC_VISIBLE",
                    },
                    {
                        "variant_ref": "v_failure",
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


def _state() -> dict:
    rows = []
    for occurrence_id, actor_id in (("o_success", "actor_a"), ("o_failure", "actor_b")):
        rows.append(
            {
                "action_occurrence_candidate_id": occurrence_id,
                "actor_identity_candidate_ids": [actor_id],
                "action_family_candidates": ["PASS"],
                "occurrence_topology": "SINGLE_ACTOR_ACTION",
                "required_participant_scope": "ACTOR_ONLY",
                "binding_state": "SINGLE_ACTOR_TRACE_VISIBLE_CANDIDATE",
                "provider_direction_candidates": ["FORWARD"],
                "primary_consequence_candidates": ["SAME_TEAM_CONTINUATION_CANDIDATE"],
            }
        )
    return {
        "status": "PASS",
        "occurrence_state_transition_projections": rows,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _consequence() -> dict:
    return {
        "status": "REVIEW_REQUIRED",
        "source_consequence_horizon": {
            "horizon_definition_state": "DECLARED_SOURCE_HORIZON",
            "horizon_basis": "FIXED_TIME_WITH_LAYER_CAP_VISIBLE_TRACE_SEARCH",
            "window_seconds": [5.0, 8.0, 12.0],
            "maximum_window_seconds": 12.0,
            "max_follow_up_time_layers": 3,
            "right_censoring_assessed": False,
        },
        "right_censoring_assessed": False,
        "no_visible_followup_is_failure": False,
        "followup_is_terminal_outcome_truth": False,
        "projection_is_causal_truth": False,
        "ensuing_terminal_support_is_causal_truth": False,
        "admitted_followup_horizon_sensitivity_is_terminal_outcome_truth": False,
        "occurrence_consequence_projections": [
            {
                "action_occurrence_candidate_id": "o_success",
                "followup_observation_status": "VISIBLE_FOLLOWUP",
                "process_continuation_status": "PROCESS_CONTINUES_VISIBLE_CANDIDATE",
                "terminal_status": "TERMINAL_STATE_UNRESOLVED",
                "observation_status": "ORDER_ADMITTED_WITHIN_DECLARED_SOURCE_HORIZON",
                "consequence_signal_candidates": ["SAME_TEAM_FOLLOW_UP_VISIBLE"],
                "primary_consequence_candidates": ["SAME_TEAM_CONTINUATION_CANDIDATE"],
                "visible_consequence_support": True,
                "terminal_outcome_support_visible": False,
                "ensuing_terminal_support_visible": False,
                "ensuing_derived_consequence_support_visible": False,
                "admitted_followup_horizon_sensitivity_state": "STABLE_ACROSS_DECLARED_WINDOWS",
                "admitted_followup_horizon_sensitivity_tested": True,
                "admitted_followup_horizon_sensitive": False,
            },
            {
                "action_occurrence_candidate_id": "o_failure",
                "followup_observation_status": "VISIBLE_FOLLOWUP",
                "process_continuation_status": "PROCESS_CONTINUES_VISIBLE_CANDIDATE",
                "terminal_status": "TERMINAL_STATE_UNRESOLVED",
                "observation_status": "ORDER_ADMITTED_WITHIN_DECLARED_SOURCE_HORIZON",
                "consequence_signal_candidates": ["SAME_TEAM_FOLLOW_UP_VISIBLE"],
                "primary_consequence_candidates": ["SAME_TEAM_CONTINUATION_CANDIDATE"],
                "visible_consequence_support": True,
                "terminal_outcome_support_visible": False,
                "ensuing_terminal_support_visible": False,
                "ensuing_derived_consequence_support_visible": False,
                "admitted_followup_horizon_sensitivity_state": "SENSITIVE_ACROSS_DECLARED_WINDOWS",
                "admitted_followup_horizon_sensitivity_tested": True,
                "admitted_followup_horizon_sensitive": True,
            },
        ],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def test_variant_delta_carries_admitted_followup_horizon_sensitivity() -> None:
    result = build_grammar_stable_variant_feature_delta(
        _sequence_variants(), _process_variants(), _state(), _consequence()
    )
    row = result["grammar_stable_variant_feature_delta_records"][0]
    assert row["admitted_followup_horizon_sensitivity_surface_consumed"] is True
    assert row["admitted_followup_horizon_sensitivity_tested"] is True
    assert row["admitted_followup_horizon_sensitive_variant_count"] == 1
    assert row["admitted_followup_horizon_sensitivity_incomplete_variant_count"] == 0
    tokens = {
        item["feature_token"]
        for item in row["consequence_feature_difference_candidates"]
    }
    assert "admitted_followup_horizon_sensitivity_state:STABLE_ACROSS_DECLARED_WINDOWS" in tokens
    assert "admitted_followup_horizon_sensitivity_state:SENSITIVE_ACROSS_DECLARED_WINDOWS" in tokens
    assert "variant_admitted_followup_horizon_sensitive:family_1" in result["review_hits"]
    assert row["admitted_followup_horizon_sensitivity_is_terminal_outcome_truth"] is False


def test_challenge_exposes_horizon_sensitive_variant_as_withdrawal_risk() -> None:
    delta = build_grammar_stable_variant_feature_delta(
        _sequence_variants(), _process_variants(), _state(), _consequence()
    )
    challenge = build_variant_feature_challenge_projection(delta, _process_variants())
    consequence_rows = [
        row
        for row in challenge["variant_feature_challenge_records"]
        if row["feature_surface"] == "CONSEQUENCE"
    ]
    assert consequence_rows
    assert any(
        "ADMITTED_FOLLOWUP_HORIZON_SENSITIVE" in row["challenge_reasons"]
        for row in consequence_rows
    )
    assert any(
        "WITHDRAW_OR_QUALIFY_IF_DIFFERENCE_IS_NOT_STABLE_ACROSS_ADMITTED_CONSEQUENCE_HORIZONS"
        in row["withdrawal_conditions"]
        for row in consequence_rows
    )
    assert challenge["professional_finding_emit_allowed"] is False
    assert challenge["consequence_horizon_sensitivity_can_be_ignored"] is False


def test_safe_finding_emit_is_lowered_by_horizon_sensitive_challenge_even_when_other_support_is_clean() -> None:
    sequence = {
        "safe_finding_handoff_candidates": [
            {
                "safe_finding_handoff_candidate_id": "sfh_1",
                "support": {"visible_success_sequence_refs": ["s1"]},
                "counterevidence": {"visible_failure_sequence_refs": ["s2"]},
            }
        ]
    }
    admission = {
        "status": "PASS",
        "safe_finding_admission_decisions": [
            {
                "source_safe_finding_handoff_ref": "sfh_1",
                "decision": "EMIT",
                "decision_reasons": [],
                "claim_output_allowed": True,
                "claim_ceiling": "DEFEASIBLE_MATCH_LOCAL_PROFESSIONAL_FINDING_ONLY",
                "admitted_independent_support_count": 2,
            }
        ],
        "review_hits": [],
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
    challenge = {
        "status": "REVIEW_REQUIRED",
        "variant_feature_challenge_records": [
            {
                "variant_feature_challenge_id": "vfc_horizon",
                "source_process_variant_family_ref": "family_1",
                "challenge_reasons": ["ADMITTED_FOLLOWUP_HORIZON_SENSITIVE"],
                "counter_scenario_candidates": [
                    "CONSEQUENCE_HORIZON_DEFINITION_MAY_CHANGE_APPARENT_DIFFERENCE"
                ],
                "withdrawal_conditions": [
                    "WITHDRAW_OR_QUALIFY_IF_DIFFERENCE_IS_NOT_STABLE_ACROSS_ADMITTED_CONSEQUENCE_HORIZONS"
                ],
                "relevant_coverage_incomplete_variant_count": 0,
                "dependency_independence_proven": True,
                "statistical_independence_proven": True,
                "professional_finding_emit_allowed": False,
            }
        ],
        "difference_rows_are_independent_evidence_votes": False,
        "feature_absence_is_counterevidence": False,
        "no_visible_followup_is_failure": False,
        "unassessed_censoring_can_be_treated_as_failure": False,
        "professional_finding_emit_allowed": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
    out = apply_variant_feature_challenge_to_admission(
        sequence, admission, challenge, _process_variants()
    )
    row = out["safe_finding_admission_decisions"][0]
    assert row["decision"] == "DOWNGRADE"
    assert row["claim_output_allowed"] is False
    assert "VARIANT_FEATURE_CHALLENGE_CONSEQUENCE_HORIZON_UNRESOLVED" in row["decision_reasons"]
    assert out["professional_finding_emitted_count"] == 0
    assert out["unresolved_consequence_horizon_can_authorize_emit"] is False
