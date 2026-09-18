from __future__ import annotations

import pytest

from hpfa.modules.core.visible_action_sequence_candidates_lite.src.safe_finding_occurrence_consequence_burden_adapter import (
    apply_occurrence_consequence_burden_to_admission,
    build_binary_visible_outcome_identification_bound,
)


def _sequence() -> dict:
    return {
        "safe_finding_handoff_candidates": [
            {
                "safe_finding_handoff_candidate_id": "sfh_1",
                "support": {"visible_success_sequence_refs": ["s1"]},
                "counterevidence": {"visible_failure_sequence_refs": ["s2"]},
            }
        ]
    }


def _admission(decision: str = "EMIT") -> dict:
    return {
        "status": "PASS",
        "safe_finding_admission_decisions": [
            {
                "source_safe_finding_handoff_ref": "sfh_1",
                "decision": decision,
                "decision_reasons": [],
                "claim_output_allowed": decision == "EMIT",
                "claim_ceiling": (
                    "DEFEASIBLE_MATCH_LOCAL_PROFESSIONAL_FINDING_ONLY"
                    if decision == "EMIT"
                    else "MATCH_LOCAL_SAFE_FINDING_CUE_ONLY"
                ),
            }
        ],
        "safe_finding_admission_decision_count": 1,
        "finding_status_counts": {
            "EMIT": 1 if decision == "EMIT" else 0,
            "DOWNGRADE": 1 if decision == "DOWNGRADE" else 0,
            "ABSTAIN": 0,
        },
        "professional_finding_emitted_count": 1 if decision == "EMIT" else 0,
        "claim_output_allowed_count": 1 if decision == "EMIT" else 0,
        "review_hits": [],
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _process_variant() -> dict:
    return {
        "observable_process_variant_families": [
            {
                "observable_process_variant_family_id": "family_1",
                "member_records": [
                    {
                        "sequence_ref": "s1",
                        "visible_outcome_state": "SUCCESS_SEMANTIC_VISIBLE",
                        "supporting_action_occurrence_candidate_ids": ["o1"],
                    },
                    {
                        "sequence_ref": "s2",
                        "visible_outcome_state": "FAILURE_SEMANTIC_VISIBLE",
                        "supporting_action_occurrence_candidate_ids": ["o2"],
                    },
                ],
            }
        ]
    }


def _occurrence_payload(rows: list[dict]) -> dict:
    return {
        "occurrence_consequence_projections": rows,
        "no_visible_followup_is_failure": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _row(
    occurrence: str,
    *,
    followup: str,
    censoring_status: str,
    assessed: bool = True,
    right_censored: bool = False,
) -> dict:
    return {
        "action_occurrence_candidate_id": occurrence,
        "followup_observation_status": followup,
        "right_censoring_status": censoring_status,
        "right_censoring_assessed": assessed,
        "right_censored": right_censored,
    }


def test_fully_observed_no_followup_is_neutral_not_failure() -> None:
    out = apply_occurrence_consequence_burden_to_admission(
        _sequence(),
        _admission("EMIT"),
        _process_variant(),
        _occurrence_payload([
            _row(
                "o1",
                followup="NO_VISIBLE_FOLLOWUP",
                censoring_status="COMPLETE_TO_DECLARED_HORIZON_NO_ADMITTED_FOLLOWUP",
            ),
            _row(
                "o2",
                followup="VISIBLE_FOLLOWUP",
                censoring_status="NOT_CENSORED_ADMITTED_FOLLOWUP_OBSERVED",
            ),
        ]),
    )
    decision = out["safe_finding_admission_decisions"][0]
    profile = decision["consequence_observation_burden_profile"]
    assert decision["decision"] == "EMIT"
    assert decision["claim_output_allowed"] is True
    assert profile["fully_observed_no_visible_followup_occurrence_count"] == 1
    assert profile["followup_unresolved_occurrence_count"] == 0
    assert profile["right_censored_occurrence_count"] == 0
    assert profile["no_visible_followup_is_failure"] is False
    assert out["fully_observed_no_visible_followup_is_failure"] is False


def test_followup_unresolved_downgrades_otherwise_emit_eligible_finding() -> None:
    out = apply_occurrence_consequence_burden_to_admission(
        _sequence(),
        _admission("EMIT"),
        _process_variant(),
        _occurrence_payload([
            _row(
                "o1",
                followup="FOLLOWUP_UNRESOLVED",
                censoring_status="CENSORING_NOT_CAUSE_ANCHOR_SUPPORT_VISIBLE",
            ),
            _row(
                "o2",
                followup="VISIBLE_FOLLOWUP",
                censoring_status="NOT_CENSORED_ADMITTED_FOLLOWUP_OBSERVED",
            ),
        ]),
    )
    decision = out["safe_finding_admission_decisions"][0]
    assert decision["decision"] == "DOWNGRADE"
    assert decision["claim_output_allowed"] is False
    assert "FOLLOWUP_OBSERVATION_UNRESOLVED_BURDEN" in decision["decision_reasons"]
    assert decision["consequence_observation_burden_profile"]["followup_unresolved_occurrence_count"] == 1
    assert out["occurrence_consequence_observation_burden_can_authorize_emit"] is False


def test_right_censored_observation_downgrades_without_calling_failure() -> None:
    out = apply_occurrence_consequence_burden_to_admission(
        _sequence(),
        _admission("EMIT"),
        _process_variant(),
        _occurrence_payload([
            _row(
                "o1",
                followup="NO_VISIBLE_FOLLOWUP",
                censoring_status="RIGHT_CENSORED_BY_ADMIN_BOUNDARY",
                right_censored=True,
            ),
            _row(
                "o2",
                followup="VISIBLE_FOLLOWUP",
                censoring_status="NOT_CENSORED_ADMITTED_FOLLOWUP_OBSERVED",
            ),
        ]),
    )
    decision = out["safe_finding_admission_decisions"][0]
    assert decision["decision"] == "DOWNGRADE"
    assert "RIGHT_CENSORED_OBSERVATION_BURDEN" in decision["decision_reasons"]
    profile = decision["consequence_observation_burden_profile"]
    assert profile["right_censored_occurrence_count"] == 1
    assert profile["right_censoring_is_failure"] is False
    assert out["right_censoring_is_failure"] is False


def test_missing_occurrence_consequence_row_is_unresolved_not_zero() -> None:
    out = apply_occurrence_consequence_burden_to_admission(
        _sequence(),
        _admission("EMIT"),
        _process_variant(),
        _occurrence_payload([
            _row(
                "o1",
                followup="VISIBLE_FOLLOWUP",
                censoring_status="NOT_CENSORED_ADMITTED_FOLLOWUP_OBSERVED",
            )
        ]),
    )
    decision = out["safe_finding_admission_decisions"][0]
    assert decision["decision"] == "DOWNGRADE"
    assert "CONSEQUENCE_OBSERVATION_COVERAGE_UNRESOLVED" in decision["decision_reasons"]
    assert decision["consequence_observation_burden_profile"]["missing_occurrence_consequence_count"] == 1


def test_existing_downgrade_can_never_be_upgraded() -> None:
    out = apply_occurrence_consequence_burden_to_admission(
        _sequence(),
        _admission("DOWNGRADE"),
        _process_variant(),
        _occurrence_payload([
            _row(
                "o1",
                followup="VISIBLE_FOLLOWUP",
                censoring_status="NOT_CENSORED_ADMITTED_FOLLOWUP_OBSERVED",
            ),
            _row(
                "o2",
                followup="VISIBLE_FOLLOWUP",
                censoring_status="NOT_CENSORED_ADMITTED_FOLLOWUP_OBSERVED",
            ),
        ]),
    )
    decision = out["safe_finding_admission_decisions"][0]
    assert decision["decision"] == "DOWNGRADE"
    assert decision["claim_output_allowed"] is False
    assert out["professional_finding_emitted_count"] == 0


def test_point_identified_visible_outcome_rate_when_no_eligible_outcome_is_unresolved() -> None:
    out = apply_occurrence_consequence_burden_to_admission(
        _sequence(),
        _admission("DOWNGRADE"),
        _process_variant(),
        _occurrence_payload([
            _row("o1", followup="VISIBLE_FOLLOWUP", censoring_status="NOT_CENSORED_ADMITTED_FOLLOWUP_OBSERVED"),
            _row("o2", followup="VISIBLE_FOLLOWUP", censoring_status="NOT_CENSORED_ADMITTED_FOLLOWUP_OBSERVED"),
        ]),
    )
    profile = out["safe_finding_admission_decisions"][0]["consequence_observation_burden_profile"]
    assert profile["bound_state"] == "POINT_IDENTIFIED_OBSERVED_RATE"
    assert profile["resolved_success_n"] == 1
    assert profile["resolved_failure_n"] == 1
    assert profile["unresolved_eligible_n"] == 0
    assert profile["eligible_total_n"] == 2
    assert profile["lower_bound"] == pytest.approx(0.5)
    assert profile["upper_bound"] == pytest.approx(0.5)
    assert profile["identification_interval_is_confidence_interval"] is False
    assert profile["rate_bound_can_authorize_emit"] is False


def test_all_unresolved_known_eligible_units_have_full_zero_one_identification_interval() -> None:
    bound = build_binary_visible_outcome_identification_bound(
        resolved_success_n=0,
        resolved_failure_n=0,
        unresolved_eligible_n=3,
        denominator_membership_admitted=True,
        target_outcome_semantics_fixed=True,
        eligible_denominator_basis="TEST_KNOWN_ELIGIBLE",
    )
    assert bound["bound_state"] == "PARTIALLY_IDENTIFIED_VISIBLE_OUTCOME_RATE"
    assert bound["eligible_total_n"] == 3
    assert bound["lower_bound"] == pytest.approx(0.0)
    assert bound["upper_bound"] == pytest.approx(1.0)
    assert bound["unknown_eligible_is_failure"] is False
    assert bound["unknown_eligible_is_success"] is False


def test_unresolved_denominator_membership_never_emits_numeric_bound() -> None:
    bound = build_binary_visible_outcome_identification_bound(
        resolved_success_n=2,
        resolved_failure_n=1,
        unresolved_eligible_n=1,
        denominator_membership_admitted=False,
        target_outcome_semantics_fixed=True,
        eligible_denominator_basis="TEST_UNRESOLVED_DENOMINATOR",
    )
    assert bound["bound_state"] == "BOUND_UNRESOLVED"
    assert bound["eligible_total_n"] is None
    assert bound["lower_bound"] is None
    assert bound["upper_bound"] is None
    assert "ELIGIBLE_DENOMINATOR_MEMBERSHIP_UNRESOLVED" in bound["bound_review_reasons"]


def test_unresolved_process_family_member_widens_bound_without_becoming_failure() -> None:
    process = _process_variant()
    process["observable_process_variant_families"][0]["member_records"].append({
        "sequence_ref": "s3",
        "visible_outcome_state": None,
        "supporting_action_occurrence_candidate_ids": ["o3"],
    })
    out = apply_occurrence_consequence_burden_to_admission(
        _sequence(),
        _admission("DOWNGRADE"),
        process,
        _occurrence_payload([
            _row("o1", followup="VISIBLE_FOLLOWUP", censoring_status="NOT_CENSORED_ADMITTED_FOLLOWUP_OBSERVED"),
            _row("o2", followup="VISIBLE_FOLLOWUP", censoring_status="NOT_CENSORED_ADMITTED_FOLLOWUP_OBSERVED"),
        ]),
    )
    profile = out["safe_finding_admission_decisions"][0]["consequence_observation_burden_profile"]
    assert profile["bound_state"] == "PARTIALLY_IDENTIFIED_VISIBLE_OUTCOME_RATE"
    assert profile["resolved_success_n"] == 1
    assert profile["resolved_failure_n"] == 1
    assert profile["unresolved_eligible_n"] == 1
    assert profile["eligible_total_n"] == 3
    assert profile["lower_bound"] == pytest.approx(1 / 3)
    assert profile["upper_bound"] == pytest.approx(2 / 3)


def test_duplicate_family_member_sequence_does_not_inflate_eligible_denominator() -> None:
    process = _process_variant()
    process["observable_process_variant_families"][0]["member_records"].append({
        "sequence_ref": "s1",
        "visible_outcome_state": "SUCCESS_SEMANTIC_VISIBLE",
        "supporting_action_occurrence_candidate_ids": ["o1"],
    })
    out = apply_occurrence_consequence_burden_to_admission(
        _sequence(),
        _admission("DOWNGRADE"),
        process,
        _occurrence_payload([
            _row("o1", followup="VISIBLE_FOLLOWUP", censoring_status="NOT_CENSORED_ADMITTED_FOLLOWUP_OBSERVED"),
            _row("o2", followup="VISIBLE_FOLLOWUP", censoring_status="NOT_CENSORED_ADMITTED_FOLLOWUP_OBSERVED"),
        ]),
    )
    profile = out["safe_finding_admission_decisions"][0]["consequence_observation_burden_profile"]
    assert profile["eligible_total_n"] == 2
    assert profile["resolved_success_n"] == 1
    assert profile["resolved_failure_n"] == 1
    assert profile["burden_counts_are_independent_support_counts"] is False


def test_right_censoring_never_relabels_already_resolved_visible_outcome_as_failure() -> None:
    out = apply_occurrence_consequence_burden_to_admission(
        _sequence(),
        _admission("DOWNGRADE"),
        _process_variant(),
        _occurrence_payload([
            _row(
                "o1",
                followup="NO_VISIBLE_FOLLOWUP",
                censoring_status="RIGHT_CENSORED_BY_ADMIN_BOUNDARY",
                right_censored=True,
            ),
            _row("o2", followup="VISIBLE_FOLLOWUP", censoring_status="NOT_CENSORED_ADMITTED_FOLLOWUP_OBSERVED"),
        ]),
    )
    profile = out["safe_finding_admission_decisions"][0]["consequence_observation_burden_profile"]
    assert profile["right_censored_occurrence_count"] == 1
    assert profile["right_censoring_is_failure"] is False
    assert profile["bound_state"] == "POINT_IDENTIFIED_OBSERVED_RATE"
    assert profile["resolved_success_n"] == 1
    assert profile["resolved_failure_n"] == 1
