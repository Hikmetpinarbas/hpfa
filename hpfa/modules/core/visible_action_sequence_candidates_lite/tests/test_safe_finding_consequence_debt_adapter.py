from __future__ import annotations

from hpfa.modules.core.visible_action_sequence_candidates_lite.src.safe_finding_variant_feature_challenge_adapter import (
    apply_variant_feature_challenge_to_admission,
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


def _admission() -> dict:
    return {
        "status": "PASS",
        "safe_finding_admission_decisions": [
            {
                "source_safe_finding_handoff_ref": "sfh_1",
                "decision": "EMIT",
                "decision_reasons": [],
                "claim_output_allowed": True,
                "claim_ceiling": "DEFEASIBLE_MATCH_LOCAL_PROFESSIONAL_FINDING_ONLY",
                "admitted_independent_support_count": 2,
                "dependency_independence_proven": True,
                "statistical_independence_proven": True,
            }
        ],
        "safe_finding_admission_decision_count": 1,
        "finding_status_counts": {"EMIT": 1, "DOWNGRADE": 0, "ABSTAIN": 0},
        "professional_finding_emitted_count": 1,
        "claim_output_allowed_count": 1,
        "review_hits": [],
        "hard_block_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _process_variant() -> dict:
    return {
        "status": "PASS",
        "observable_process_variant_families": [
            {
                "observable_process_variant_family_id": "family_1",
                "member_records": [
                    {"sequence_ref": "s1", "visible_outcome_state": "SUCCESS_SEMANTIC_VISIBLE"},
                    {"sequence_ref": "s2", "visible_outcome_state": "FAILURE_SEMANTIC_VISIBLE"},
                ],
            }
        ],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _challenge(*, reasons: list[str]) -> dict:
    return {
        "status": "REVIEW_REQUIRED",
        "variant_feature_challenge_records": [
            {
                "variant_feature_challenge_id": "vfc_1",
                "source_process_variant_family_ref": "family_1",
                "challenge_reasons": reasons,
                "counter_scenario_candidates": ["CONSEQUENCE_HORIZON_DEFINITION_MAY_CHANGE_APPARENT_DIFFERENCE"],
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


def test_unresolved_consequence_horizon_downgrades_otherwise_emit_eligible_finding() -> None:
    out = apply_variant_feature_challenge_to_admission(
        _sequence(),
        _admission(),
        _challenge(reasons=["CONSEQUENCE_HORIZON_SENSITIVITY_NOT_TESTED"]),
        _process_variant(),
    )
    row = out["safe_finding_admission_decisions"][0]
    assert row["decision"] == "DOWNGRADE"
    assert row["claim_output_allowed"] is False
    assert "VARIANT_FEATURE_CHALLENGE_CONSEQUENCE_HORIZON_UNRESOLVED" in row["decision_reasons"]
    assert row["admitted_independent_support_count"] == 2
    assert out["unresolved_consequence_horizon_can_authorize_emit"] is False
    assert out["professional_finding_emitted_count"] == 0


def test_unresolved_censoring_downgrades_otherwise_emit_eligible_finding() -> None:
    out = apply_variant_feature_challenge_to_admission(
        _sequence(),
        _admission(),
        _challenge(reasons=["RIGHT_CENSORING_NOT_ASSESSED", "NO_VISIBLE_FOLLOWUP_CENSORING_UNRESOLVED"]),
        _process_variant(),
    )
    row = out["safe_finding_admission_decisions"][0]
    assert row["decision"] == "DOWNGRADE"
    assert "VARIANT_FEATURE_CHALLENGE_CENSORING_UNRESOLVED" in row["decision_reasons"]
    assert out["unresolved_consequence_censoring_can_authorize_emit"] is False
    assert out["professional_finding_emitted_count"] == 0


def test_unrelated_challenge_reason_does_not_add_consequence_specific_downgrade() -> None:
    out = apply_variant_feature_challenge_to_admission(
        _sequence(),
        _admission(),
        _challenge(reasons=["SAMPLE_STRENGTH_UNCALIBRATED"]),
        _process_variant(),
    )
    row = out["safe_finding_admission_decisions"][0]
    assert row["decision"] == "EMIT"
    assert "VARIANT_FEATURE_CHALLENGE_CONSEQUENCE_HORIZON_UNRESOLVED" not in row["decision_reasons"]
    assert "VARIANT_FEATURE_CHALLENGE_CENSORING_UNRESOLVED" not in row["decision_reasons"]


def test_censoring_failure_promotion_fails_closed() -> None:
    bad = _challenge(reasons=[])
    bad["unassessed_censoring_can_be_treated_as_failure"] = True
    out = apply_variant_feature_challenge_to_admission(
        _sequence(), _admission(), bad, _process_variant()
    )
    assert out["status"] == "FAIL_CLOSED"
    assert "variant_feature_challenge_censoring_failure_lock_breached" in out["hard_block_hits"]
    assert out["safe_finding_admission_decisions"] == []
