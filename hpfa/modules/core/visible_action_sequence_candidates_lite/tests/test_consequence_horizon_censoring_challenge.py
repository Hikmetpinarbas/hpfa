from __future__ import annotations

from hpfa.modules.core.visible_action_sequence_candidates_lite.src.variant_feature_challenge_projection import (
    build_variant_feature_challenge_projection,
)


def _process_variant() -> dict:
    return {
        "status": "PASS",
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "observable_process_variant_families": [
            {
                "observable_process_variant_family_id": "fam_1",
                "same_grammar_visible_outcome_variation_observed": True,
                "team_identity_candidate_ids": ["team_a"],
                "period_candidates": ["1"],
                "dependency_group_refs": ["dep_1"],
                "dependency_group_ref_count": 1,
                "family_is_independent_recurrence_truth": False,
            }
        ],
    }


def _feature_delta(*, contract_present: bool = True, feature_token: str = "followup_observation_status:NO_VISIBLE_FOLLOWUP") -> dict:
    row = {
        "grammar_stable_variant_feature_delta_id": "delta_1",
        "source_process_variant_family_ref": "fam_1",
        "context_coverage_incomplete_variant_count": 0,
        "consequence_coverage_incomplete_variant_count": 0,
        "consequence_observation_state_features_consumed": contract_present,
        "consequence_horizon_definition_state": (
            "DECLARED_SOURCE_HORIZON" if contract_present else "HORIZON_UNSPECIFIED"
        ),
        "consequence_horizon_sensitivity_tested": False,
        "right_censoring_assessed": False,
        "context_feature_difference_candidates": [],
        "consequence_feature_difference_candidates": [
            {
                "feature_token": feature_token,
                "success_visible_numerator": 0,
                "success_eligible_denominator": 10,
                "failure_visible_numerator": 4,
                "failure_eligible_denominator": 10,
                "descriptive_rate_delta_success_minus_failure": -0.4,
                "dependency_independence_proven": False,
                "statistical_independence_proven": False,
            }
        ],
    }
    return {
        "status": "PASS",
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "outcome_used_only_as_partition_label": True,
        "outcome_used_to_define_features": False,
        "feature_absence_is_counterevidence": False,
        "no_visible_followup_is_failure": False,
        "grammar_stable_variant_feature_delta_records": [row],
    }


def test_consequence_feature_challenge_exposes_horizon_and_censoring_debt() -> None:
    result = build_variant_feature_challenge_projection(_feature_delta(), _process_variant())
    row = result["variant_feature_challenge_records"][0]
    reasons = set(row["challenge_reasons"])
    assert row["consequence_observation_contract_present"] is True
    assert row["consequence_horizon_definition_state"] == "DECLARED_SOURCE_HORIZON"
    assert row["consequence_horizon_sensitivity_tested"] is False
    assert row["right_censoring_assessed"] is False
    assert "CONSEQUENCE_HORIZON_SENSITIVITY_NOT_TESTED" in reasons
    assert "RIGHT_CENSORING_NOT_ASSESSED" in reasons
    assert "NO_VISIBLE_FOLLOWUP_CENSORING_UNRESOLVED" in reasons
    assert "CONSEQUENCE_HORIZON_DEFINITION_MAY_CHANGE_APPARENT_DIFFERENCE" in row["counter_scenario_candidates"]
    assert "WITHDRAW_OR_QUALIFY_IF_DIFFERENCE_IS_NOT_STABLE_ACROSS_ADMITTED_CONSEQUENCE_HORIZONS" in row["withdrawal_conditions"]
    assert "consequence_horizon_sensitivity_not_tested" in result["review_hits"]
    assert "right_censoring_not_assessed" in result["review_hits"]
    assert result["no_visible_followup_is_failure"] is False
    assert result["professional_finding_emit_allowed"] is False


def test_fully_observed_no_followup_does_not_invent_unresolved_censoring() -> None:
    payload = _feature_delta()
    row = payload["grammar_stable_variant_feature_delta_records"][0]
    row["right_censoring_assessed"] = True
    row["right_censored_variant_count"] = 0
    row["right_censoring_incomplete_variant_count"] = 0
    row["fully_observed_no_followup_variant_count"] = 4

    result = build_variant_feature_challenge_projection(payload, _process_variant())
    challenge = result["variant_feature_challenge_records"][0]
    reasons = set(challenge["challenge_reasons"])

    assert challenge["right_censoring_assessed"] is True
    assert challenge["right_censored_variant_count"] == 0
    assert challenge["right_censoring_incomplete_variant_count"] == 0
    assert challenge["fully_observed_no_followup_variant_count"] == 4
    assert "RIGHT_CENSORING_NOT_ASSESSED" not in reasons
    assert "RIGHT_CENSORING_PARTIAL" not in reasons
    assert "RIGHT_CENSORED_VARIANT_PRESENT" not in reasons
    assert "NO_VISIBLE_FOLLOWUP_CENSORING_UNRESOLVED" not in reasons
    assert challenge["no_visible_followup_is_failure"] is False


def test_legacy_feature_delta_does_not_invent_new_horizon_debt() -> None:
    result = build_variant_feature_challenge_projection(
        _feature_delta(contract_present=False, feature_token="primary_consequence_candidates:OPPONENT_HANDOVER_CANDIDATE"),
        _process_variant(),
    )
    row = result["variant_feature_challenge_records"][0]
    reasons = set(row["challenge_reasons"])
    assert row["consequence_observation_contract_present"] is False
    assert "CONSEQUENCE_HORIZON_SENSITIVITY_NOT_TESTED" not in reasons
    assert "RIGHT_CENSORING_NOT_ASSESSED" not in reasons
    assert "consequence_horizon_sensitivity_not_tested" not in result["review_hits"]
    assert "right_censoring_not_assessed" not in result["review_hits"]


def test_no_visible_followup_failure_promotion_fails_closed() -> None:
    payload = _feature_delta()
    payload["no_visible_followup_is_failure"] = True
    result = build_variant_feature_challenge_projection(payload, _process_variant())
    assert result["status"] == "FAIL_CLOSED"
    assert "no_visible_followup_failure_lock_breached" in result["hard_block_hits"]
    assert result["variant_feature_challenge_records"] == []


def test_challenge_does_not_create_causal_or_independent_evidence() -> None:
    result = build_variant_feature_challenge_projection(_feature_delta(), _process_variant())
    row = result["variant_feature_challenge_records"][0]
    assert row["difference_is_failure_cause_truth"] is False
    assert row["feature_absence_is_counterevidence"] is False
    assert row["no_visible_followup_is_failure"] is False
    assert result["difference_rows_are_independent_evidence_votes"] is False
    assert result["projection_creates_new_evidence"] is False
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["true_action_count"] == "UNKNOWN"
    assert result["production_release"] is False
