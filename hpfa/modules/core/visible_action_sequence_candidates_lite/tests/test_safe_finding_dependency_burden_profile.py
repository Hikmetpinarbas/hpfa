from pathlib import Path

from hpfa.modules.core.visible_action_sequence_candidates_lite.src.safe_finding_admission_projection import (
    build_safe_finding_admission,
)


def _handoff(*, independent: int, dep: bool, stat: bool) -> dict:
    blocking = [] if independent > 0 and dep and stat else ["INDEPENDENT_SUPPORT_NOT_ADMITTED"]
    return {
        "safe_finding_handoff_candidate_id": "sfh_dependency_profile",
        "professional_finding_emit_allowed": False,
        "safe_finding_handoff_is_professional_finding_truth": False,
        "safe_finding_handoff_is_tactical_truth": False,
        "safe_finding_handoff_is_causal_truth": False,
        "safe_finding_handoff_is_coach_intention_truth": False,
        "same_timestamp_internal_ordering_allowed": False,
        "source_row_order_is_temporal_truth": False,
        "same_comparison_design_counterevidence_required": True,
        "where_when": {"shared_anchor_time_layer_ref": "layer_shared_anchor"},
        "support": {
            "admitted_independent_support_count": independent,
            "dependency_independence_proven": dep,
            "statistical_independence_proven": stat,
            "eligible_denominator": 2,
            "support_state": "DESCRIPTIVE_ONLY_DEPENDENCY_DOMINATED",
        },
        "counterevidence": {"comparable_counterexample_refs": ["counter_1"]},
        "evidence_sufficiency": {
            "state": (
                "NO_BLOCKING_DIMENSION_VISIBLE_BUT_EMIT_NOT_AUTHORIZED_HERE"
                if not blocking
                else "INSUFFICIENT_FOR_PROFESSIONAL_EMIT"
            ),
            "blocking_dimensions": blocking,
            "dimensions": {
                "independent_support": {
                    "admitted_count": independent,
                    "dependency_independence_proven": dep,
                    "statistical_independence_proven": stat,
                },
                "eligible_case_coverage": {
                    "eligible_case_count": 2,
                    "resolved_outcome_case_count": 2,
                    "unresolved_outcome_case_count": 0,
                    "accounted_case_count": 2,
                    "state": "COMPLETE_RESOLVED_CASE_COVERAGE",
                },
                "episode_spread": {"count": 2, "state": "OBSERVED"},
                "context_coverage": {"state": "COMPLETE"},
                "actor_spread": {"count": 2, "single_actor_concentration": False},
                "challenge_surface": {"comparable_counterexample_pair_count": 1},
            },
        },
        "alternative_explanations": [
            {
                "code": "SHARED_ANCHOR_DEPENDENCY",
                "meaning": "Visible branches share one admitted anchor.",
            }
        ],
        "uncertainty": {
            "concentration_warnings": [
                "SINGLE_SHARED_ANCHOR_CONCENTRATION",
                "DEPENDENCY_DOMINATED_SHARED_ANCHOR_BRANCHES",
            ]
        },
        "safe_meaning": "MATCH_LOCAL_VISIBLE_VARIATION_ONLY",
        "forbidden_inference": ["CAUSALITY", "INDEPENDENT_RECURRENCE_SUPPORT"],
        "withdrawal_conditions": ["WITHDRAW_IF_BINDING_INVALIDATED"],
    }


def _payload(handoff: dict) -> dict:
    return {
        "comparable_outcome_counterevidence_status": "PASS",
        "safe_finding_handoff_candidates": [handoff],
        "review_hits": [],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def test_shared_anchor_dependency_is_explained_not_only_boolean_blocked() -> None:
    out = build_safe_finding_admission(_payload(_handoff(independent=0, dep=False, stat=False)))
    assert out["finding_status_counts"] == {"EMIT": 0, "DOWNGRADE": 1, "ABSTAIN": 0}
    row = out["safe_finding_admission_decisions"][0]
    burden = row["dependency_burden_profile"]
    assert burden["profile_state"] == "SHARED_VISIBLE_ANCHOR_DEPENDENCY_DOMINATED"
    assert burden["shared_anchor_dependency_state"] == "PRESENT"
    assert burden["reflection_group_burden_state"] == "UNRESOLVED_NOT_EXPLICITLY_BOUND"
    assert burden["dependency_group_burden_state"] == "UNRESOLVED_OR_SHARED_DEPENDENCY_PRESENT"
    assert burden["aggregate_reconciliation_burden_state"] == "NOT_IN_CURRENT_BRANCH_COMPARISON_DESIGN"
    assert burden["dependency_burden_is_confidence_score"] is False
    assert burden["burden_dimensions_compensate_each_other"] is False
    assert "SHARED_ANCHOR_DEPENDENCY_BURDEN" in row["decision_reasons"]
    assert "REFLECTION_GROUP_BURDEN_UNRESOLVED" in row["decision_reasons"]
    assert "DEPENDENCY_GROUP_BURDEN_UNRESOLVED" in row["decision_reasons"]
    assert out["dependency_burden_profiled_decision_count"] == 1
    assert out["shared_anchor_dependency_dominated_decision_count"] == 1


def test_clean_independent_support_is_not_downgraded_by_explanatory_profile() -> None:
    out = build_safe_finding_admission(_payload(_handoff(independent=2, dep=True, stat=True)))
    assert out["finding_status_counts"] == {"EMIT": 1, "DOWNGRADE": 0, "ABSTAIN": 0}
    row = out["safe_finding_admission_decisions"][0]
    burden = row["dependency_burden_profile"]
    assert burden["profile_state"] == "NO_BLOCKING_DEPENDENCY_BURDEN_VISIBLE"
    assert burden["dependency_burden_can_authorize_independence"] is False
    assert "SHARED_ANCHOR_DEPENDENCY_BURDEN" not in row["decision_reasons"]


def test_dependency_profile_never_becomes_a_composite_score() -> None:
    out = build_safe_finding_admission(_payload(_handoff(independent=0, dep=False, stat=False)))
    assert out["dependency_burden_profile_is_non_compensatory"] is True
    assert out["dependency_burden_numeric_score_allowed"] is False
    assert out["dependency_burden_can_authorize_independence"] is False
    burden = out["safe_finding_admission_decisions"][0]["dependency_burden_profile"]
    assert burden["absence_of_explicit_reflection_burden_means_independence"] is False
    assert burden["shared_anchor_count_is_independent_recurrence_count"] is False


def test_no_sample_match_identity_leak() -> None:
    source = Path(
        "hpfa/modules/core/visible_action_sequence_candidates_lite/src/safe_finding_admission_projection.py"
    ).read_text(encoding="utf-8")
    for token in ("Sporting", "Galatasaray", "Fenerbahce", "Fenerbahçe", "Roma", "14.09.2026"):
        assert token not in source
