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
                "admitted_independent_support_count": 2,
                "dependency_independence_proven": True,
                "statistical_independence_proven": True,
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
        "status": "REVIEW_REQUIRED",
        "observable_process_variant_families": [
            {
                "observable_process_variant_family_id": "family_1",
                "member_records": [
                    {
                        "sequence_ref": "s1",
                        "visible_outcome_state": "SUCCESS_SEMANTIC_VISIBLE",
                    },
                    {
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


def _challenge(*, partial: bool, dep: bool, stat: bool) -> dict:
    return {
        "status": "REVIEW_REQUIRED",
        "variant_feature_challenge_records": [
            {
                "variant_feature_challenge_id": "vfc_1",
                "source_process_variant_family_ref": "family_1",
                "challenge_reasons": ["SAMPLE_STRENGTH_UNCALIBRATED"],
                "counter_scenario_candidates": [
                    "SAMPLE_COMPOSITION_MAY_EXPLAIN_DIFFERENCE"
                ],
                "withdrawal_conditions": [
                    "WITHDRAW_OR_QUALIFY_IF_DIFFERENCE_DISAPPEARS_IN_ADMITTED_COMPARABLE_CONTEXT"
                ],
                "relevant_coverage_incomplete_variant_count": 1 if partial else 0,
                "dependency_independence_proven": dep,
                "statistical_independence_proven": stat,
                "professional_finding_emit_allowed": False,
            }
        ],
        "difference_rows_are_independent_evidence_votes": False,
        "feature_absence_is_counterevidence": False,
        "professional_finding_emit_allowed": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def test_partial_matched_challenge_downgrades_emit_without_changing_support() -> None:
    out = apply_variant_feature_challenge_to_admission(
        _sequence(),
        _admission("EMIT"),
        _challenge(partial=True, dep=True, stat=True),
        _process_variant(),
    )
    row = out["safe_finding_admission_decisions"][0]
    assert row["decision"] == "DOWNGRADE"
    assert row["claim_output_allowed"] is False
    assert row["admitted_independent_support_count"] == 2
    assert "VARIANT_FEATURE_CHALLENGE_COVERAGE_PARTIAL" in row["decision_reasons"]
    assert row["variant_feature_challenge_refs"] == ["vfc_1"]
    assert out["variant_feature_challenge_can_increase_support"] is False
    assert out["variant_feature_challenge_can_authorize_emit"] is False


def test_unproven_challenge_independence_downgrades_emit() -> None:
    out = apply_variant_feature_challenge_to_admission(
        _sequence(),
        _admission("EMIT"),
        _challenge(partial=False, dep=False, stat=False),
        _process_variant(),
    )
    reasons = out["safe_finding_admission_decisions"][0]["decision_reasons"]
    assert "VARIANT_FEATURE_CHALLENGE_DEPENDENCY_INDEPENDENCE_UNPROVEN" in reasons
    assert "VARIANT_FEATURE_CHALLENGE_STATISTICAL_INDEPENDENCE_UNPROVEN" in reasons
    assert out["professional_finding_emitted_count"] == 0


def test_right_censored_challenge_downgrades_emit_without_calling_it_failure() -> None:
    challenge = _challenge(partial=False, dep=True, stat=True)
    challenge["variant_feature_challenge_records"][0]["challenge_reasons"] = [
        "RIGHT_CENSORED_VARIANT_PRESENT",
        "NO_VISIBLE_FOLLOWUP_CENSORING_UNRESOLVED",
    ]
    out = apply_variant_feature_challenge_to_admission(
        _sequence(),
        _admission("EMIT"),
        challenge,
        _process_variant(),
    )
    row = out["safe_finding_admission_decisions"][0]
    assert row["decision"] == "DOWNGRADE"
    assert row["claim_output_allowed"] is False
    assert "VARIANT_FEATURE_CHALLENGE_CENSORING_UNRESOLVED" in row["decision_reasons"]
    assert "RIGHT_CENSORED_VARIANT_PRESENT" in row["variant_feature_challenge_reason_codes"]
    assert out["professional_finding_emitted_count"] == 0
    assert out["unresolved_consequence_censoring_can_authorize_emit"] is False


def test_complete_challenge_can_preserve_but_never_create_emit() -> None:
    out = apply_variant_feature_challenge_to_admission(
        _sequence(),
        _admission("DOWNGRADE"),
        _challenge(partial=False, dep=True, stat=True),
        _process_variant(),
    )
    row = out["safe_finding_admission_decisions"][0]
    assert row["decision"] == "DOWNGRADE"
    assert row["claim_output_allowed"] is False
    assert row["variant_feature_challenge_refs"] == ["vfc_1"]
    assert out["professional_finding_emitted_count"] == 0


def test_missing_challenge_never_silently_preserves_emit() -> None:
    out = apply_variant_feature_challenge_to_admission(
        _sequence(),
        _admission("EMIT"),
        None,
        _process_variant(),
    )
    row = out["safe_finding_admission_decisions"][0]
    assert row["decision"] == "DOWNGRADE"
    assert "VARIANT_FEATURE_CHALLENGE_NOT_AVAILABLE" in row["decision_reasons"]
    assert out["status"] == "REVIEW_REQUIRED"


def test_challenge_truth_lock_breach_fails_closed() -> None:
    bad = _challenge(partial=False, dep=True, stat=True)
    bad["professional_finding_emit_allowed"] = True
    out = apply_variant_feature_challenge_to_admission(
        _sequence(),
        _admission("EMIT"),
        bad,
        _process_variant(),
    )
    assert out["status"] == "FAIL_CLOSED"
    assert out["safe_finding_admission_decisions"] == []
    assert "variant_feature_challenge_emit_lock_not_false" in out["hard_block_hits"]
