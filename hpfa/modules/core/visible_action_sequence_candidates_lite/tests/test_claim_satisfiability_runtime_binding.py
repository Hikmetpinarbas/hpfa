from __future__ import annotations

from hpfa.modules.core.visible_action_sequence_candidates_lite.src.claim_satisfiability_runtime_binding import (
    bind_claim_satisfiability,
)


def _sequence(*, independent_support: int = 0, independent: bool = False) -> dict:
    return {
        "safe_finding_handoff_candidates": [
            {
                "safe_finding_handoff_candidate_id": "sfh_1",
                "source_first_supported_branch_divergence_ref": "div_1",
                "what_visible": {"state": "VISIBLE_VARIATION"},
                "support": {
                    "admitted_independent_support_count": independent_support,
                    "dependency_independence_proven": independent,
                    "statistical_independence_proven": independent,
                },
            }
        ],
        "first_supported_branch_divergence_candidates": [
            {
                "first_supported_branch_divergence_id": "div_1",
                "production_release": False,
                "canonical_event_count": "UNKNOWN",
                "true_action_count": "UNKNOWN",
                "same_timestamp_internal_ordering_allowed": False,
                "source_row_order_is_temporal_truth": False,
                "branch_profiles": [
                    {
                        "neighbor_action_family_counts": {"TURNOVER": 1},
                        "semantic_profiles": [
                            {"progression_values": ["FORWARD_PROGRESSIVE"]}
                        ],
                    }
                ],
            }
        ],
    }


def _admission(*, episode_spread: bool = True) -> dict:
    return {
        "safe_finding_admission_decisions": [
            {
                "source_safe_finding_handoff_ref": "sfh_1",
                "variant_support_episode_spread_observed": episode_spread,
            }
        ]
    }


def _claim(*, emit: bool = False) -> dict:
    return {
        "status": "PASS",
        "analyst_output_contracts": [
            {
                "source_safe_finding_handoff_ref": "sfh_1",
                "professional_emit_allowed": emit,
                "claim_scope": "DEFEASIBLE_MATCH_LOCAL_PROFESSIONAL_FINDING_ONLY"
                if emit
                else "MATCH_LOCAL_OBSERVED_VARIATION_CUE_ONLY",
            }
        ],
        "analyst_output_contract_count": 1,
        "professional_emit_allowed": emit,
        "professional_emit_allowed_count": 1 if emit else 0,
        "review_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _by_family(row: dict) -> dict[str, dict]:
    return {
        item["claim_family"]: item
        for item in row.get("claim_satisfiability_assessments") or []
    }


def test_binding_exposes_bounded_family_states_without_opening_emit() -> None:
    result = bind_claim_satisfiability(_sequence(), _admission(), _claim())
    row = result["analyst_output_contracts"][0]
    families = _by_family(row)

    assert result["claim_satisfiability_gate_consumed"] is True
    assert row["claim_satisfiability_gate_state"] == "SATISFIED_WITH_CEILING"
    assert families["MATCH_LOCAL_VISIBLE_VARIATION"]["state"] == "SATISFIED_WITH_CEILING"
    assert families["PROGRESSION_ACCESS_DESCRIPTION"]["state"] == "SATISFIED_WITH_CEILING"
    assert families["RETENTION_LOSS_DESCRIPTION"]["state"] == "SATISFIED_WITH_CEILING"
    assert families["MATCH_LOCAL_RECURRENCE_CANDIDATE"]["state"] == "UNSATISFIED_MISSING_REQUIRED_CAPABILITY"
    assert families["CAUSALITY"]["state"] == "UNSATISFIABLE_CURRENT_PRODUCT_CEILING"
    assert families["TACTICAL_PATTERN_TRUTH"]["state"] == "UNSATISFIABLE_CURRENT_PRODUCT_CEILING"
    assert row["professional_emit_allowed"] is False
    assert result["professional_emit_allowed_count"] == 0
    assert result["claim_satisfiability_gate_can_authorize_emit"] is False
    assert result["claim_satisfiability_gate_creates_new_evidence"] is False
    assert result["claim_satisfiability_gate_can_strengthen_claim_ceiling"] is False


def test_binding_can_only_close_a_prior_emit_when_source_lineage_is_missing() -> None:
    sequence = _sequence()
    sequence["first_supported_branch_divergence_candidates"] = []
    result = bind_claim_satisfiability(sequence, _admission(), _claim(emit=True))
    row = result["analyst_output_contracts"][0]

    assert row["professional_emit_allowed"] is False
    assert row["claim_scope"] == "NO_CLAIM_OUTPUT"
    assert row["claim_satisfiability_gate_blocked_professional_emit"] is True
    assert result["professional_emit_allowed"] is False
    assert result["professional_emit_allowed_count"] == 0
    assert result["status"] == "REVIEW_REQUIRED"


def test_recurrence_candidate_requires_noncompensating_independence_and_episode_spread() -> None:
    result = bind_claim_satisfiability(
        _sequence(independent_support=2, independent=True),
        _admission(episode_spread=True),
        _claim(),
    )
    families = _by_family(result["analyst_output_contracts"][0])
    recurrence = families["MATCH_LOCAL_RECURRENCE_CANDIDATE"]

    assert recurrence["state"] == "SATISFIED_WITH_CEILING"
    assert recurrence["admitted_independent_support_count"] == 2
    assert recurrence["dependency_independence_proven"] is True
    assert recurrence["statistical_independence_proven"] is True
    assert recurrence["episode_spread_observed"] is True
    assert recurrence["gate_can_authorize_emit"] is False
    assert recurrence["recurrence_is_causality"] is False
