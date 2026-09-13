from __future__ import annotations

from hpfa.modules.core.visible_action_sequence_candidates_lite.src.analyst_output_claim_contract_projection import (
    ADMITTED_PROFESSIONAL_FINDING_SCOPE,
    ANALYST_OUTPUT_CLAIM_SCOPE,
    NO_CLAIM_SCOPE,
    build_analyst_output_claim_contract,
)


def _source() -> dict:
    return {
        "safe_finding_handoff_professional_emit_allowed": False,
        "safe_finding_handoff_candidates": [
            {
                "safe_finding_handoff_candidate_id": "sfh_1",
                "professional_finding_emit_allowed": False,
                "evidence_sufficiency": {
                    "state": "NO_BLOCKING_DIMENSION_VISIBLE_BUT_EMIT_NOT_AUTHORIZED_HERE",
                    "blocking_dimensions": [],
                },
                "forbidden_inference": ["CAUSALITY", "COACH_INTENTION"],
            }
        ],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _admission(decision: str, allowed: bool, *, status: str = "PASS") -> dict:
    return {
        "status": status,
        "safe_finding_admission_decisions": [
            {
                "source_safe_finding_handoff_ref": "sfh_1",
                "decision": decision,
                "claim_output_allowed": allowed,
            }
        ],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def test_legacy_no_admission_stays_fail_safe() -> None:
    out = build_analyst_output_claim_contract(_source())
    assert out["professional_emit_allowed"] is False
    assert out["professional_emit_allowed_count"] == 0
    assert out["safe_finding_admission_consumed"] is False
    row = out["analyst_output_contracts"][0]
    assert row["safe_finding_admission_decision"] == "NOT_EVALUATED"
    assert row["claim_scope"] == ANALYST_OUTPUT_CLAIM_SCOPE


def test_explicit_emit_opens_only_defeasible_match_local_professional_finding() -> None:
    out = build_analyst_output_claim_contract(_source(), _admission("EMIT", True))
    assert out["professional_emit_allowed"] is True
    assert out["professional_emit_allowed_count"] == 1
    row = out["analyst_output_contracts"][0]
    assert row["professional_emit_allowed"] is True
    assert row["claim_scope"] == ADMITTED_PROFESSIONAL_FINDING_SCOPE
    assert row["raw_rate_may_be_labeled_probability"] is False
    assert row["match_local_observation_may_be_generalized_cross_match"] is False
    assert out["review_required_admission_can_authorize_emit"] is False


def test_review_required_emit_is_blocked_from_professional_output() -> None:
    out = build_analyst_output_claim_contract(
        _source(),
        _admission("EMIT", True, status="REVIEW_REQUIRED"),
    )
    assert out["status"] == "REVIEW_REQUIRED"
    assert out["professional_emit_allowed"] is False
    assert out["professional_emit_allowed_count"] == 0
    row = out["analyst_output_contracts"][0]
    assert row["safe_finding_admission_decision"] == "ABSTAIN"
    assert row["professional_emit_allowed"] is False
    assert row["claim_scope"] == NO_CLAIM_SCOPE
    assert "safe_finding_admission_review_required" in out["review_hits"]
    assert "emit_blocked_by_review_required_admission:sfh_1" in out["review_hits"]
    assert out["review_required_admission_can_authorize_emit"] is False


def test_review_required_downgrade_preserves_review_debt_without_emit() -> None:
    out = build_analyst_output_claim_contract(
        _source(),
        _admission("DOWNGRADE", False, status="REVIEW_REQUIRED"),
    )
    assert out["status"] == "REVIEW_REQUIRED"
    assert out["professional_emit_allowed"] is False
    row = out["analyst_output_contracts"][0]
    assert row["safe_finding_admission_decision"] == "DOWNGRADE"
    assert row["claim_scope"] == ANALYST_OUTPUT_CLAIM_SCOPE
    assert "safe_finding_admission_review_required" in out["review_hits"]


def test_downgrade_keeps_professional_emit_closed() -> None:
    out = build_analyst_output_claim_contract(_source(), _admission("DOWNGRADE", False))
    row = out["analyst_output_contracts"][0]
    assert out["professional_emit_allowed"] is False
    assert row["professional_emit_allowed"] is False
    assert row["claim_scope"] == ANALYST_OUTPUT_CLAIM_SCOPE


def test_abstain_closes_claim_output_entirely() -> None:
    out = build_analyst_output_claim_contract(_source(), _admission("ABSTAIN", False))
    row = out["analyst_output_contracts"][0]
    assert row["professional_emit_allowed"] is False
    assert row["claim_scope"] == NO_CLAIM_SCOPE
    assert row["raw_rate_may_be_reported_as_observed_sample_description"] is False


def test_missing_admission_decision_is_review_required_not_emit() -> None:
    admission = _admission("DOWNGRADE", False)
    admission["safe_finding_admission_decisions"] = []
    out = build_analyst_output_claim_contract(_source(), admission)
    assert out["status"] == "REVIEW_REQUIRED"
    assert out["professional_emit_allowed"] is False
    assert "admission_decision_missing:sfh_1" in out["review_hits"]


def test_admission_fail_closed_blocks_claim_contract() -> None:
    admission = _admission("EMIT", True)
    admission["status"] = "FAIL_CLOSED"
    out = build_analyst_output_claim_contract(_source(), admission)
    assert out["status"] == "FAIL_CLOSED"
    assert out["analyst_output_contracts"] == []
    assert out["professional_emit_allowed"] is False


def test_unrecognized_admission_status_fails_closed() -> None:
    out = build_analyst_output_claim_contract(
        _source(),
        _admission("EMIT", True, status="UNKNOWN_STATUS"),
    )
    assert out["status"] == "FAIL_CLOSED"
    assert out["professional_emit_allowed"] is False
    assert out["analyst_output_contracts"] == []


def test_emit_label_without_claim_output_permission_abstains() -> None:
    out = build_analyst_output_claim_contract(_source(), _admission("EMIT", False))
    row = out["analyst_output_contracts"][0]
    assert out["status"] == "REVIEW_REQUIRED"
    assert row["safe_finding_admission_decision"] == "ABSTAIN"
    assert row["claim_scope"] == NO_CLAIM_SCOPE
    assert row["professional_emit_allowed"] is False
