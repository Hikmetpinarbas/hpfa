from __future__ import annotations

from hpfa.modules.core.visible_action_sequence_candidates_lite.src.safe_finding_occurrence_consequence_burden_adapter import (
    apply_occurrence_consequence_burden_to_admission,
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
