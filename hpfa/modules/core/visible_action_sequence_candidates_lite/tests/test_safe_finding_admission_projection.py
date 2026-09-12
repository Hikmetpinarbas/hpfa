from __future__ import annotations

from hpfa.modules.core.visible_action_sequence_candidates_lite.src.safe_finding_admission_projection import (
    build_safe_finding_admission,
)


def _handoff(ref: str, *, independent: int, dep: bool, stat: bool, blocking: list[str]) -> dict:
    return {
        "safe_finding_handoff_candidate_id": ref,
        "professional_finding_emit_allowed": False,
        "safe_finding_handoff_is_professional_finding_truth": False,
        "safe_finding_handoff_is_tactical_truth": False,
        "safe_finding_handoff_is_causal_truth": False,
        "safe_finding_handoff_is_coach_intention_truth": False,
        "same_timestamp_internal_ordering_allowed": False,
        "source_row_order_is_temporal_truth": False,
        "support": {
            "admitted_independent_support_count": independent,
            "dependency_independence_proven": dep,
            "statistical_independence_proven": stat,
        },
        "counterevidence": {
            "comparable_counterexample_refs": [f"counter_{ref}"],
        },
        "evidence_sufficiency": {
            "state": (
                "NO_BLOCKING_DIMENSION_VISIBLE_BUT_EMIT_NOT_AUTHORIZED_HERE"
                if not blocking
                else "INSUFFICIENT_FOR_PROFESSIONAL_EMIT"
            ),
            "blocking_dimensions": blocking,
        },
        "alternative_explanations": [
            {"code": "ALT", "meaning": "visible alternative explanation"}
        ],
        "safe_meaning": "MATCH_LOCAL_VISIBLE_VARIATION_ONLY",
        "forbidden_inference": ["CAUSALITY", "COACH_INTENTION"],
        "withdrawal_conditions": ["WITHDRAW_IF_BINDING_INVALIDATED"],
    }


def _payload(handoffs: list[dict]) -> dict:
    return {
        "comparable_outcome_counterevidence_status": "REVIEW_REQUIRED",
        "safe_finding_handoff_candidates": handoffs,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def test_emit_when_all_required_evidence_dimensions_are_admitted() -> None:
    out = build_safe_finding_admission(
        _payload([_handoff("sfh_emit", independent=2, dep=True, stat=True, blocking=[])])
    )
    assert out["finding_status_counts"] == {"EMIT": 1, "DOWNGRADE": 0, "ABSTAIN": 0}
    assert out["professional_finding_emitted_count"] == 1
    assert out["safe_finding_admission_decisions"][0]["claim_output_allowed"] is True


def test_downgrade_when_independence_is_not_admitted() -> None:
    out = build_safe_finding_admission(
        _payload([
            _handoff(
                "sfh_down",
                independent=0,
                dep=False,
                stat=False,
                blocking=["INDEPENDENT_SUPPORT_NOT_ADMITTED"],
            )
        ])
    )
    assert out["finding_status_counts"] == {"EMIT": 0, "DOWNGRADE": 1, "ABSTAIN": 0}
    row = out["safe_finding_admission_decisions"][0]
    assert row["claim_output_allowed"] is False
    assert "INDEPENDENT_SUPPORT_NOT_ADMITTED" in row["decision_reasons"]


def test_abstain_when_safe_finding_contract_is_incomplete() -> None:
    row = _handoff("sfh_abstain", independent=1, dep=True, stat=True, blocking=[])
    row["withdrawal_conditions"] = []
    out = build_safe_finding_admission(_payload([row]))
    assert out["finding_status_counts"] == {"EMIT": 0, "DOWNGRADE": 0, "ABSTAIN": 1}
    assert out["status"] == "REVIEW_REQUIRED"


def test_projection_does_not_copy_evidence_payloads_or_create_evidence() -> None:
    out = build_safe_finding_admission(
        _payload([_handoff("sfh_small", independent=1, dep=True, stat=True, blocking=[])])
    )
    row = out["safe_finding_admission_decisions"][0]
    assert "support" not in row
    assert "counterevidence" not in row
    assert "alternative_explanations" not in row
    assert out["decision_rows_copy_evidence_payloads"] is False
    assert out["decision_projection_creates_new_evidence"] is False
    assert out["decision_projection_reconstructs_sequences"] is False


def test_truth_lock_violation_abstains_instead_of_emitting() -> None:
    row = _handoff("sfh_lock", independent=3, dep=True, stat=True, blocking=[])
    row["safe_finding_handoff_is_causal_truth"] = True
    out = build_safe_finding_admission(_payload([row]))
    assert out["finding_status_counts"]["ABSTAIN"] == 1
    assert out["professional_finding_emitted_count"] == 0


def test_global_truth_claim_fails_closed() -> None:
    payload = _payload([])
    payload["canonical_event_count"] = 123
    out = build_safe_finding_admission(payload)
    assert out["status"] == "FAIL_CLOSED"
    assert out["safe_finding_admission_decisions"] == []
