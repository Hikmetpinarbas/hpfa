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
            "eligible_denominator": 2,
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
                "episode_spread": {
                    "count": 2,
                    "state": "OBSERVED",
                },
                "context_coverage": {"state": "COMPLETE"},
                "actor_spread": {
                    "count": 2,
                    "single_actor_concentration": False,
                },
                "challenge_surface": {
                    "comparable_counterexample_pair_count": 1,
                },
            },
        },
        "alternative_explanations": [
            {"code": "ALT", "meaning": "visible alternative explanation"}
        ],
        "safe_meaning": "MATCH_LOCAL_VISIBLE_VARIATION_ONLY",
        "forbidden_inference": ["CAUSALITY", "COACH_INTENTION"],
        "withdrawal_conditions": ["WITHDRAW_IF_BINDING_INVALIDATED"],
    }


def _payload(
    handoffs: list[dict],
    *,
    source_status: str = "PASS",
    review_hits: list[str] | None = None,
    scoped_counterevidence_reviews: list[str] | None = None,
    declare_scoped_surface: bool = False,
) -> dict:
    payload = {
        "comparable_outcome_counterevidence_status": source_status,
        "safe_finding_handoff_candidates": handoffs,
        "review_hits": list(review_hits or []),
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
    if declare_scoped_surface:
        payload["comparable_outcome_counterevidence_review_hits"] = list(
            scoped_counterevidence_reviews or []
        )
        payload["comparable_outcome_counterevidence_review_scope"] = (
            "COMPARABLE_OUTCOME_PROJECTION_ONLY"
        )
    return payload


def test_emit_when_all_required_evidence_dimensions_are_admitted() -> None:
    out = build_safe_finding_admission(
        _payload([_handoff("sfh_emit", independent=2, dep=True, stat=True, blocking=[])])
    )
    assert out["finding_status_counts"] == {"EMIT": 1, "DOWNGRADE": 0, "ABSTAIN": 0}
    assert out["professional_finding_emitted_count"] == 1
    row = out["safe_finding_admission_decisions"][0]
    assert row["claim_output_allowed"] is True
    assert row["evidence_profile_dimensions_validated"] is True
    assert row["eligible_denominator"] == 2
    assert row["unresolved_outcome_case_count"] == 0


def test_missing_required_evidence_profile_dimension_abstains() -> None:
    row = _handoff("sfh_missing_dimension", independent=2, dep=True, stat=True, blocking=[])
    del row["evidence_sufficiency"]["dimensions"]["eligible_case_coverage"]
    out = build_safe_finding_admission(_payload([row]))
    assert out["finding_status_counts"] == {"EMIT": 0, "DOWNGRADE": 0, "ABSTAIN": 1}
    decision = out["safe_finding_admission_decisions"][0]
    assert decision["claim_output_allowed"] is False
    assert (
        "evidence_sufficiency_dimension_missing:eligible_case_coverage"
        in decision["decision_reasons"]
    )


def test_unresolved_eligible_case_burden_downgrades_even_if_blocking_list_is_stale() -> None:
    row = _handoff("sfh_unresolved", independent=2, dep=True, stat=True, blocking=[])
    coverage = row["evidence_sufficiency"]["dimensions"]["eligible_case_coverage"]
    coverage.update(
        {
            "resolved_outcome_case_count": 1,
            "unresolved_outcome_case_count": 1,
            "accounted_case_count": 2,
            "state": "COMPLETE_CASE_ACCOUNTING_WITH_UNRESOLVED_OUTCOMES",
        }
    )
    out = build_safe_finding_admission(_payload([row]))
    assert out["finding_status_counts"] == {"EMIT": 0, "DOWNGRADE": 1, "ABSTAIN": 0}
    decision = out["safe_finding_admission_decisions"][0]
    assert "UNRESOLVED_OUTCOME_BURDEN" in decision["decision_reasons"]
    assert "OUTCOME_COVERAGE_PARTIAL_OR_UNKNOWN" in decision["decision_reasons"]
    assert decision["unresolved_outcome_case_count"] == 1


def test_context_and_actor_profile_bind_directly_without_blocking_summary() -> None:
    row = _handoff("sfh_context_actor", independent=2, dep=True, stat=True, blocking=[])
    row["evidence_sufficiency"]["dimensions"]["context_coverage"]["state"] = "PARTIAL_PERIOD_ONLY"
    row["evidence_sufficiency"]["dimensions"]["actor_spread"] = {
        "count": 1,
        "single_actor_concentration": True,
    }
    out = build_safe_finding_admission(_payload([row]))
    assert out["finding_status_counts"] == {"EMIT": 0, "DOWNGRADE": 1, "ABSTAIN": 0}
    decision = out["safe_finding_admission_decisions"][0]
    assert "CONTEXT_COVERAGE_PARTIAL_OR_UNKNOWN" in decision["decision_reasons"]
    assert "SINGLE_ACTOR_CONCENTRATION" in decision["decision_reasons"]


def test_unscoped_upstream_review_cannot_authorize_emit() -> None:
    out = build_safe_finding_admission(
        _payload(
            [_handoff("sfh_review", independent=2, dep=True, stat=True, blocking=[])],
            source_status="REVIEW_REQUIRED",
        )
    )
    assert out["status"] == "REVIEW_REQUIRED"
    assert out["finding_status_counts"] == {"EMIT": 0, "DOWNGRADE": 1, "ABSTAIN": 0}
    row = out["safe_finding_admission_decisions"][0]
    assert row["claim_output_allowed"] is False
    assert "UPSTREAM_COUNTEREVIDENCE_REVIEW_UNSCOPED" in row["decision_reasons"]
    assert out["unscoped_upstream_review_can_authorize_emit"] is False


def test_pass_envelope_with_unscoped_review_hits_cannot_authorize_emit() -> None:
    out = build_safe_finding_admission(
        _payload(
            [_handoff("sfh_pass_review", independent=2, dep=True, stat=True, blocking=[])],
            source_status="PASS",
            review_hits=["serialization_or_replay_review"],
        )
    )
    assert out["status"] == "REVIEW_REQUIRED"
    assert out["finding_status_counts"] == {"EMIT": 0, "DOWNGRADE": 1, "ABSTAIN": 0}
    row = out["safe_finding_admission_decisions"][0]
    assert row["claim_output_allowed"] is False
    assert "UPSTREAM_COUNTEREVIDENCE_REVIEW_UNSCOPED" in row["decision_reasons"]
    assert "counterevidence_upstream_pass_with_review_hits" in out["review_hits"]
    assert out["pass_with_unscoped_review_hits_can_authorize_emit"] is False


def test_scoped_counterevidence_surface_ignores_unrelated_sequence_review_hits() -> None:
    out = build_safe_finding_admission(
        _payload(
            [_handoff("sfh_scoped", independent=2, dep=True, stat=True, blocking=[])],
            source_status="PASS",
            review_hits=["unrelated_sequence_review"],
            scoped_counterevidence_reviews=[],
            declare_scoped_surface=True,
        )
    )
    assert out["status"] == "PASS"
    assert out["finding_status_counts"] == {"EMIT": 1, "DOWNGRADE": 0, "ABSTAIN": 0}
    row = out["safe_finding_admission_decisions"][0]
    assert row["claim_output_allowed"] is True
    assert "UPSTREAM_COUNTEREVIDENCE_REVIEW_UNSCOPED" not in row["decision_reasons"]
    assert out["counterevidence_review_scope"] == "COMPARABLE_OUTCOME_PROJECTION_ONLY"
    assert out["counterevidence_scoped_review_surface_declared"] is True


def test_scoped_counterevidence_review_still_blocks_emit() -> None:
    out = build_safe_finding_admission(
        _payload(
            [_handoff("sfh_scoped_review", independent=2, dep=True, stat=True, blocking=[])],
            source_status="PASS",
            review_hits=["unrelated_sequence_review"],
            scoped_counterevidence_reviews=["comparison_binding_review_required"],
            declare_scoped_surface=True,
        )
    )
    assert out["status"] == "REVIEW_REQUIRED"
    assert out["finding_status_counts"] == {"EMIT": 0, "DOWNGRADE": 1, "ABSTAIN": 0}
    row = out["safe_finding_admission_decisions"][0]
    assert row["claim_output_allowed"] is False
    assert "UPSTREAM_COUNTEREVIDENCE_REVIEW_UNSCOPED" in row["decision_reasons"]


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


def test_empty_alternative_object_cannot_satisfy_challenge() -> None:
    row = _handoff("sfh_empty_alt", independent=2, dep=True, stat=True, blocking=[])
    row["counterevidence"]["comparable_counterexample_refs"] = []
    row["evidence_sufficiency"]["dimensions"]["challenge_surface"][
        "comparable_counterexample_pair_count"
    ] = 0
    row["alternative_explanations"] = [{}]
    out = build_safe_finding_admission(_payload([row]))
    assert out["finding_status_counts"] == {"EMIT": 0, "DOWNGRADE": 0, "ABSTAIN": 1}
    decision = out["safe_finding_admission_decisions"][0]
    assert decision["claim_output_allowed"] is False
    assert "alternative_explanation_incomplete" in decision["decision_reasons"]


def test_truth_bearing_alternative_fields_are_rejected() -> None:
    row = _handoff("sfh_truth_alt", independent=2, dep=True, stat=True, blocking=[])
    row["alternative_explanations"] = [
        {
            "code": "ALT",
            "meaning": "candidate explanation",
            "causality": True,
        }
    ]
    out = build_safe_finding_admission(_payload([row]))
    assert out["finding_status_counts"] == {"EMIT": 0, "DOWNGRADE": 0, "ABSTAIN": 1}
    decision = out["safe_finding_admission_decisions"][0]
    assert decision["claim_output_allowed"] is False
    assert "alternative_explanation_schema_not_allowlisted" in decision["decision_reasons"]


def test_uncertainty_truth_lock_violation_abstains() -> None:
    row = _handoff("sfh_uncertainty_lock", independent=2, dep=True, stat=True, blocking=[])
    row["uncertainty"] = {"no_visible_followup_is_failure": True}
    out = build_safe_finding_admission(_payload([row]))
    assert out["finding_status_counts"]["ABSTAIN"] == 1
    assert out["professional_finding_emitted_count"] == 0


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
    assert out["evidence_profile_dimensions_required_for_emit"] is True
    assert out["evidence_profile_dimensions_compensate_each_other"] is False


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


def test_unresolved_typed_defeat_target_cannot_authorize_emit():
    row = _handoff("sfh_typed_unresolved", independent=2, dep=True, stat=True, blocking=[])
    row["typed_defeat_contract"] = {
        "observed_defeat_state": "UNRESOLVED_NO_EXPLICIT_CLAIM_COMPONENT_TARGET",
        "observed_defeat_type": "DEFEAT_TYPE_UNRESOLVED",
        "observed_target_component_type": None,
        "observed_target_component_ref": None,
        "observed_source_counterevidence_refs": ["counter_sfh_typed_unresolved"],
        "conditional_withdrawal_rules": [
            {
                "condition_code": "WITHDRAW_IF_BINDING_INVALIDATED",
                "defeat_type": "UNDERCUT",
                "target_component_type": "INFERENCE_WARRANT",
                "target_component_ref": "sfh_typed_unresolved",
                "withdrawal_effect": "ABSTAIN",
            }
        ],
        "defeat_is_causal_refutation": False,
        "defeat_is_independent_support": False,
        "defeat_creates_new_evidence": False,
        "defeat_can_authorize_emit": False,
        "defeat_can_strengthen_claim_ceiling": False,
        "withdrawal_effect_can_strengthen_claim": False,
        "rebut_without_explicit_target_allowed": False,
    }
    out = build_safe_finding_admission(_payload([row]))
    decision = out["safe_finding_admission_decisions"][0]

    assert decision["decision"] == "DOWNGRADE"
    assert decision["claim_output_allowed"] is False
    assert "TYPED_DEFEAT_TARGET_UNRESOLVED" in decision["decision_reasons"]
    assert decision["typed_defeat_profile"]["observed_defeat_type"] == "DEFEAT_TYPE_UNRESOLVED"
    assert decision["typed_defeat_can_authorize_emit"] is False
    assert decision["typed_defeat_can_strengthen_claim_ceiling"] is False


def test_typed_withdrawal_effect_cannot_strengthen_claim():
    row = _handoff("sfh_typed_bad_effect", independent=2, dep=True, stat=True, blocking=[])
    row["typed_defeat_contract"] = {
        "observed_defeat_state": "NOT_APPLICABLE_NO_OBSERVED_COUNTEREXAMPLE",
        "observed_defeat_type": "NOT_APPLICABLE",
        "observed_target_component_type": None,
        "observed_target_component_ref": None,
        "observed_source_counterevidence_refs": [],
        "conditional_withdrawal_rules": [
            {
                "condition_code": "WITHDRAW_IF_BINDING_INVALIDATED",
                "defeat_type": "UNDERCUT",
                "target_component_type": "INFERENCE_WARRANT",
                "target_component_ref": "sfh_typed_bad_effect",
                "withdrawal_effect": "STRENGTHEN",
            }
        ],
        "defeat_is_causal_refutation": False,
        "defeat_is_independent_support": False,
        "defeat_creates_new_evidence": False,
        "defeat_can_authorize_emit": False,
        "defeat_can_strengthen_claim_ceiling": False,
        "withdrawal_effect_can_strengthen_claim": False,
        "rebut_without_explicit_target_allowed": False,
    }
    out = build_safe_finding_admission(_payload([row]))
    decision = out["safe_finding_admission_decisions"][0]

    assert decision["decision"] == "ABSTAIN"
    assert decision["claim_output_allowed"] is False
    assert "typed_withdrawal_effect_unrecognized" in decision["decision_reasons"]
