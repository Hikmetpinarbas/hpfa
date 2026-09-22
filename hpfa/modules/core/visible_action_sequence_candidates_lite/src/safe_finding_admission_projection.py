from __future__ import annotations

from collections import Counter
from typing import Any

CLAIM_CEILING_EMIT = "DEFEASIBLE_MATCH_LOCAL_PROFESSIONAL_FINDING_ONLY"
CLAIM_CEILING_DOWNGRADE = "MATCH_LOCAL_SAFE_FINDING_CUE_ONLY"
CLAIM_CEILING_ABSTAIN = "NO_CLAIM_OUTPUT"
_ALLOWED_ALTERNATIVE_KEYS = {"code", "meaning"}
_ALLOWED_DEFEAT_TYPES = {"REBUT", "UNDERCUT", "UNDERMINE", "DEFEAT_TYPE_UNRESOLVED", "NOT_APPLICABLE"}
_ALLOWED_WITHDRAWAL_EFFECTS = {"PRESERVE", "DOWNGRADE", "ABSTAIN", "REVIEW_REQUIRED"}
_ALLOWED_TARGET_COMPONENT_TYPES = {
    "CONCLUSION",
    "INFERENCE_WARRANT",
    "SUPPORTING_PREMISE",
    "CHALLENGE_BINDING_WARRANT",
    "UNRESOLVED",
}
_REQUIRED_EVIDENCE_DIMENSIONS = {
    "independent_support",
    "eligible_case_coverage",
    "episode_spread",
    "context_coverage",
    "actor_spread",
    "challenge_surface",
}


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _refs(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return sorted({_clean(item) for item in value if _clean(item)})


def _nonnegative_int(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _validated_alternatives(value: Any) -> tuple[list[dict[str, str]], str | None]:
    if value is None:
        return [], None
    if not isinstance(value, list):
        return [], "alternative_explanations_invalid"

    validated: list[dict[str, str]] = []
    for row in value:
        if not isinstance(row, dict):
            return [], "alternative_explanation_not_object"
        if set(row) - _ALLOWED_ALTERNATIVE_KEYS:
            return [], "alternative_explanation_schema_not_allowlisted"
        code = _clean(row.get("code"))
        meaning = _clean(row.get("meaning"))
        if not code or not meaning:
            return [], "alternative_explanation_incomplete"
        validated.append({"code": code, "meaning": meaning})
    return validated, None


def _validated_typed_defeat_contract(value: Any) -> tuple[dict[str, Any], str | None]:
    if value is None:
        return {
            "binding_state": "NOT_AVAILABLE",
            "observed_defeat_state": "NOT_AVAILABLE",
            "observed_defeat_type": "NOT_APPLICABLE",
            "observed_source_counterevidence_refs": [],
            "conditional_withdrawal_rules": [],
            "conditional_withdrawal_rule_count": 0,
            "defeat_can_authorize_emit": False,
            "defeat_can_strengthen_claim_ceiling": False,
            "defeat_creates_new_evidence": False,
            "defeat_is_causal_refutation": False,
            "defeat_is_independent_support": False,
            "withdrawal_effect_can_strengthen_claim": False,
        }, None
    if not isinstance(value, dict):
        return {}, "typed_defeat_contract_invalid"
    for key in (
        "defeat_can_authorize_emit",
        "defeat_can_strengthen_claim_ceiling",
        "defeat_creates_new_evidence",
        "defeat_is_causal_refutation",
        "defeat_is_independent_support",
        "withdrawal_effect_can_strengthen_claim",
        "rebut_without_explicit_target_allowed",
    ):
        if value.get(key) is not False:
            return {}, f"typed_defeat_truth_lock_breached:{key}"

    observed_type = _clean(value.get("observed_defeat_type")).upper()
    observed_state = _clean(value.get("observed_defeat_state")).upper()
    target_type = _clean(value.get("observed_target_component_type")).upper()
    target_ref = _clean(value.get("observed_target_component_ref"))
    refs = _refs(value.get("observed_source_counterevidence_refs"))
    if observed_type not in _ALLOWED_DEFEAT_TYPES:
        return {}, "typed_defeat_type_unrecognized"
    if observed_type in {"REBUT", "UNDERCUT", "UNDERMINE"}:
        if target_type not in _ALLOWED_TARGET_COMPONENT_TYPES - {"UNRESOLVED"} or not target_ref:
            return {}, "typed_defeat_explicit_target_missing"
    if observed_type == "DEFEAT_TYPE_UNRESOLVED" and (target_type or target_ref):
        return {}, "typed_defeat_unresolved_target_must_remain_empty"

    rules = value.get("conditional_withdrawal_rules")
    if not isinstance(rules, list):
        return {}, "typed_withdrawal_rules_invalid"
    validated_rules: list[dict[str, Any]] = []
    for row in rules:
        if not isinstance(row, dict):
            return {}, "typed_withdrawal_rule_not_object"
        condition = _clean(row.get("condition_code"))
        defeat_type = _clean(row.get("defeat_type")).upper()
        component_type = _clean(row.get("target_component_type")).upper()
        component_ref = _clean(row.get("target_component_ref")) or None
        effect = _clean(row.get("withdrawal_effect")).upper()
        if not condition or defeat_type not in _ALLOWED_DEFEAT_TYPES:
            return {}, "typed_withdrawal_rule_incomplete"
        if component_type not in _ALLOWED_TARGET_COMPONENT_TYPES:
            return {}, "typed_withdrawal_target_type_unrecognized"
        if effect not in _ALLOWED_WITHDRAWAL_EFFECTS:
            return {}, "typed_withdrawal_effect_unrecognized"
        if defeat_type in {"REBUT", "UNDERCUT", "UNDERMINE"} and not component_ref:
            return {}, "typed_withdrawal_target_ref_missing"
        validated_rules.append({
            "condition_code": condition,
            "defeat_type": defeat_type,
            "target_component_type": component_type,
            "target_component_ref": component_ref,
            "withdrawal_effect": effect,
        })

    return {
        "binding_state": "SOURCE_BOUND_TYPED_DEFEAT_CONTRACT",
        "observed_defeat_state": observed_state or "UNRESOLVED",
        "observed_defeat_type": observed_type,
        "observed_target_component_type": target_type or None,
        "observed_target_component_ref": target_ref or None,
        "observed_source_counterevidence_refs": refs,
        "conditional_withdrawal_rules": validated_rules,
        "conditional_withdrawal_rule_count": len(validated_rules),
        "defeat_can_authorize_emit": False,
        "defeat_can_strengthen_claim_ceiling": False,
        "defeat_creates_new_evidence": False,
        "defeat_is_causal_refutation": False,
        "defeat_is_independent_support": False,
        "withdrawal_effect_can_strengthen_claim": False,
    }, None


def _dependency_burden_profile(
    handoff: dict[str, Any],
    *,
    independent_support: int,
    independence_proven: bool,
    statistical_independence_proven: bool,
) -> tuple[dict[str, Any], list[str]]:
    """Describe the dependency conditions that place apparent repetitions in unresolved independent-support state.

    This profile creates no new evidence and no score. It only exposes dependency debt
    already visible in the Safe Finding handoff. Missing reflection/dependency lineage is
    kept explicitly unresolved rather than silently treated as independent.
    """
    where_when = handoff.get("where_when") if isinstance(handoff.get("where_when"), dict) else {}
    support = handoff.get("support") if isinstance(handoff.get("support"), dict) else {}
    uncertainty = handoff.get("uncertainty") if isinstance(handoff.get("uncertainty"), dict) else {}
    alternative_codes = {
        _clean(row.get("code"))
        for row in (handoff.get("alternative_explanations") or [])
        if isinstance(row, dict) and _clean(row.get("code"))
    }
    concentration_warnings = _refs(uncertainty.get("concentration_warnings"))
    shared_anchor_ref = _clean(where_when.get("shared_anchor_time_layer_ref")) or None
    same_design = handoff.get("same_comparison_design_counterevidence_required") is True
    shared_anchor_dependency_visible = bool(
        shared_anchor_ref
        and (
            same_design
            or "SHARED_ANCHOR_DEPENDENCY" in alternative_codes
            or "SINGLE_SHARED_ANCHOR_CONCENTRATION" in concentration_warnings
            or "DEPENDENCY_DOMINATED_SHARED_ANCHOR_BRANCHES" in concentration_warnings
        )
    )

    if independent_support > 0 and independence_proven and statistical_independence_proven:
        profile_state = "NO_BLOCKING_DEPENDENCY_BURDEN_VISIBLE"
        dependency_group_state = "NO_UNRESOLVED_BLOCK_VISIBLE"
        reflection_state = "NOT_REQUIRED_TO_DOWNGRADE_CURRENT_SUPPORT"
        reasons: list[str] = []
    elif shared_anchor_dependency_visible:
        profile_state = "SHARED_VISIBLE_ANCHOR_DEPENDENCY_DOMINATED"
        dependency_group_state = "UNRESOLVED_OR_SHARED_DEPENDENCY_PRESENT"
        reflection_state = "UNRESOLVED_NOT_EXPLICITLY_BOUND"
        reasons = [
            "SHARED_ANCHOR_DEPENDENCY_BURDEN",
            "DEPENDENCY_GROUP_BURDEN_UNRESOLVED",
            "REFLECTION_GROUP_BURDEN_UNRESOLVED",
        ]
    else:
        profile_state = "DEPENDENCY_BURDEN_UNRESOLVED"
        dependency_group_state = "UNRESOLVED"
        reflection_state = "UNRESOLVED_NOT_EXPLICITLY_BOUND"
        reasons = [
            "DEPENDENCY_GROUP_BURDEN_UNRESOLVED",
            "REFLECTION_GROUP_BURDEN_UNRESOLVED",
        ]

    return {
        "profile_state": profile_state,
        "admitted_independent_support_count": independent_support,
        "dependency_independence_proven": independence_proven,
        "statistical_independence_proven": statistical_independence_proven,
        "shared_anchor_dependency_state": (
            "PRESENT" if shared_anchor_dependency_visible else "NOT_VISIBLE_OR_NOT_APPLICABLE"
        ),
        "shared_anchor_time_layer_ref": shared_anchor_ref,
        "reflection_group_burden_state": reflection_state,
        "dependency_group_burden_state": dependency_group_state,
        "aggregate_reconciliation_burden_state": "NOT_IN_CURRENT_BRANCH_COMPARISON_DESIGN",
        "support_state": _clean(support.get("support_state")) or "UNKNOWN",
        "dependency_burden_can_authorize_independence": False,
        "dependency_burden_is_confidence_score": False,
        "burden_dimensions_compensate_each_other": False,
        "absence_of_explicit_reflection_burden_means_independence": False,
        "shared_anchor_count_is_independent_recurrence_count": False,
    }, reasons


def _validated_evidence_profile(
    sufficiency: dict[str, Any],
    support: dict[str, Any],
    counterevidence: dict[str, Any],
) -> tuple[dict[str, Any] | None, str | None, list[str]]:
    dimensions = sufficiency.get("dimensions")
    if not isinstance(dimensions, dict):
        return None, "evidence_sufficiency_dimensions_missing", []
    for key in sorted(_REQUIRED_EVIDENCE_DIMENSIONS):
        if not isinstance(dimensions.get(key), dict):
            return None, f"evidence_sufficiency_dimension_missing:{key}", []

    independent = dimensions["independent_support"]
    profile_independent_support = _nonnegative_int(independent.get("admitted_count"))
    support_independent_support = _nonnegative_int(support.get("admitted_independent_support_count"))
    if profile_independent_support is None or support_independent_support is None:
        return None, "independent_support_count_invalid", []
    if profile_independent_support != support_independent_support:
        return None, "independent_support_profile_mismatch", []
    for profile_key, support_key in (
        ("dependency_independence_proven", "dependency_independence_proven"),
        ("statistical_independence_proven", "statistical_independence_proven"),
    ):
        profile_value = independent.get(profile_key)
        support_value = support.get(support_key)
        if not isinstance(profile_value, bool) or not isinstance(support_value, bool):
            return None, f"evidence_sufficiency_boolean_invalid:{profile_key}", []
        if profile_value is not support_value:
            return None, f"evidence_sufficiency_profile_mismatch:{profile_key}", []

    eligible = dimensions["eligible_case_coverage"]
    eligible_case_count = _nonnegative_int(eligible.get("eligible_case_count"))
    resolved_case_count = _nonnegative_int(eligible.get("resolved_outcome_case_count"))
    unresolved_case_count = _nonnegative_int(eligible.get("unresolved_outcome_case_count"))
    accounted_case_count = _nonnegative_int(eligible.get("accounted_case_count"))
    if None in {eligible_case_count, resolved_case_count, unresolved_case_count, accounted_case_count}:
        return None, "eligible_case_coverage_count_invalid", []
    if accounted_case_count != resolved_case_count + unresolved_case_count:
        return None, "eligible_case_coverage_accounting_mismatch", []
    support_denominator = _nonnegative_int(support.get("eligible_denominator"))
    if support_denominator is None:
        return None, "eligible_denominator_invalid", []
    if support_denominator != eligible_case_count:
        return None, "eligible_denominator_profile_mismatch", []
    eligible_state = _clean(eligible.get("state"))
    if not eligible_state:
        return None, "eligible_case_coverage_state_missing", []

    episode = dimensions["episode_spread"]
    episode_state = _clean(episode.get("state"))
    episode_count = episode.get("count")
    if not episode_state:
        return None, "episode_spread_state_missing", []
    if episode_count != "UNKNOWN" and _nonnegative_int(episode_count) is None:
        return None, "episode_spread_count_invalid", []

    context = dimensions["context_coverage"]
    context_state = _clean(context.get("state"))
    if not context_state:
        return None, "context_coverage_state_missing", []

    actor = dimensions["actor_spread"]
    actor_count = actor.get("count")
    single_actor = actor.get("single_actor_concentration")
    if actor_count != "UNKNOWN" and _nonnegative_int(actor_count) is None:
        return None, "actor_spread_count_invalid", []
    if single_actor not in {True, False, "UNKNOWN"}:
        return None, "actor_spread_concentration_state_invalid", []

    challenge = dimensions["challenge_surface"]
    challenge_pair_count = _nonnegative_int(challenge.get("comparable_counterexample_pair_count"))
    if challenge_pair_count is None:
        return None, "challenge_surface_pair_count_invalid", []
    counter_refs = _refs(counterevidence.get("comparable_counterexample_refs"))
    if challenge_pair_count != len(counter_refs):
        return None, "challenge_surface_profile_mismatch", []

    reasons: list[str] = []
    if eligible_case_count == 0:
        reasons.append("ELIGIBLE_DENOMINATOR_EMPTY")
    if unresolved_case_count > 0:
        reasons.append("UNRESOLVED_OUTCOME_BURDEN")
    if eligible_state != "COMPLETE_RESOLVED_CASE_COVERAGE":
        reasons.append("OUTCOME_COVERAGE_PARTIAL_OR_UNKNOWN")
    if episode_state == "UNKNOWN" or episode_count == "UNKNOWN":
        reasons.append("EPISODE_SPREAD_UNKNOWN")
    if context_state != "COMPLETE":
        reasons.append("CONTEXT_COVERAGE_PARTIAL_OR_UNKNOWN")
    if actor_count == "UNKNOWN" or single_actor == "UNKNOWN":
        reasons.append("ACTOR_SPREAD_UNKNOWN")
    elif single_actor is True:
        reasons.append("SINGLE_ACTOR_CONCENTRATION")
    if challenge_pair_count < 1:
        reasons.append("CHALLENGE_SURFACE_EMPTY")

    return {
        "eligible_denominator": eligible_case_count,
        "resolved_outcome_case_count": resolved_case_count,
        "unresolved_outcome_case_count": unresolved_case_count,
        "episode_spread_state": episode_state,
        "episode_spread_count": episode_count,
        "context_coverage_state": context_state,
        "actor_spread_count": actor_count,
        "single_actor_concentration": single_actor,
        "comparable_counterexample_pair_count": challenge_pair_count,
    }, None, sorted(set(reasons))


def _abstain(source_ref: str | None, *reasons: str) -> dict[str, Any]:
    return {
        "source_safe_finding_handoff_ref": source_ref,
        "decision": "ABSTAIN",
        "decision_reasons": sorted({_clean(reason) for reason in reasons if _clean(reason)}),
        "claim_output_allowed": False,
        "claim_ceiling": CLAIM_CEILING_ABSTAIN,
    }


def build_safe_finding_admission(sequence_payload: dict[str, Any]) -> dict[str, Any]:
    hard_blocks: list[str] = []
    review_hits: list[str] = []

    if sequence_payload.get("production_release") is True:
        hard_blocks.append("production_release_claimed")
    if sequence_payload.get("canonical_event_count") != "UNKNOWN":
        hard_blocks.append("canonical_event_count_claimed")
    if sequence_payload.get("true_action_count") != "UNKNOWN":
        hard_blocks.append("true_action_count_claimed")
    if sequence_payload.get("comparable_outcome_counterevidence_status") == "FAIL_CLOSED":
        hard_blocks.append("counterevidence_upstream_fail_closed")

    if hard_blocks:
        return {
            "status": "FAIL_CLOSED",
            "safe_finding_admission_decisions": [],
            "safe_finding_admission_decision_count": 0,
            "finding_status_counts": {"EMIT": 0, "DOWNGRADE": 0, "ABSTAIN": 0},
            "professional_finding_emitted_count": 0,
            "claim_output_allowed_count": 0,
            "hard_block_hits": sorted(set(hard_blocks)),
            "review_hits": [],
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
        }

    source_status = _clean(sequence_payload.get("comparable_outcome_counterevidence_status")).upper()
    scoped_review_declared = "comparable_outcome_counterevidence_review_hits" in sequence_payload
    upstream_review_hits = _refs(
        sequence_payload.get("comparable_outcome_counterevidence_review_hits")
        if scoped_review_declared
        else sequence_payload.get("review_hits")
    )
    counterevidence_review_scope = (
        "COMPARABLE_OUTCOME_PROJECTION_ONLY"
        if scoped_review_declared
        else "LEGACY_UNSCOPED_SEQUENCE_REVIEW"
    )
    source_review_unscoped = source_status == "REVIEW_REQUIRED" or bool(upstream_review_hits)
    if source_status == "REVIEW_REQUIRED":
        review_hits.append("counterevidence_upstream_review_unscoped")
    elif source_status != "PASS":
        review_hits.append(f"counterevidence_status_unrecognized:{source_status or 'UNKNOWN'}")
    if upstream_review_hits:
        review_hits.append("counterevidence_upstream_review_hits_unscoped")
        if source_status == "PASS":
            review_hits.append("counterevidence_upstream_pass_with_review_hits")

    decisions: list[dict[str, Any]] = []
    for handoff in sequence_payload.get("safe_finding_handoff_candidates") or []:
        if not isinstance(handoff, dict):
            decisions.append(_abstain(None, "handoff_not_object"))
            continue

        source_ref = _clean(handoff.get("safe_finding_handoff_candidate_id")) or None
        if source_ref is None:
            decisions.append(_abstain(None, "handoff_id_missing"))
            continue

        if handoff.get("professional_finding_emit_allowed") is not False:
            decisions.append(_abstain(source_ref, "upstream_emit_lock_not_false"))
            continue
        truth_locks = (
            handoff.get("safe_finding_handoff_is_professional_finding_truth") is False,
            handoff.get("safe_finding_handoff_is_tactical_truth") is False,
            handoff.get("safe_finding_handoff_is_causal_truth") is False,
            handoff.get("safe_finding_handoff_is_coach_intention_truth") is False,
            handoff.get("same_timestamp_internal_ordering_allowed") is False,
            handoff.get("source_row_order_is_temporal_truth") is False,
        )
        if not all(truth_locks):
            decisions.append(_abstain(source_ref, "truth_lock_missing"))
            continue

        sufficiency = handoff.get("evidence_sufficiency")
        support = handoff.get("support")
        counterevidence = handoff.get("counterevidence")
        if not isinstance(sufficiency, dict) or not isinstance(support, dict) or not isinstance(counterevidence, dict):
            decisions.append(_abstain(source_ref, "required_decision_input_missing"))
            continue

        blocking = _refs(sufficiency.get("blocking_dimensions"))
        sufficiency_state = _clean(sufficiency.get("state"))
        independent_support = support.get("admitted_independent_support_count")
        independence_proven = support.get("dependency_independence_proven") is True
        statistical_independence_proven = support.get("statistical_independence_proven") is True
        counter_refs = _refs(counterevidence.get("comparable_counterexample_refs"))
        alternatives, alternatives_error = _validated_alternatives(handoff.get("alternative_explanations"))
        withdrawals = _refs(handoff.get("withdrawal_conditions"))
        typed_defeat_profile, typed_defeat_error = _validated_typed_defeat_contract(
            handoff.get("typed_defeat_contract")
        )
        forbidden = _refs(handoff.get("forbidden_inference"))
        safe_meaning = _clean(handoff.get("safe_meaning"))

        if isinstance(independent_support, bool) or not isinstance(independent_support, int) or independent_support < 0:
            decisions.append(_abstain(source_ref, "independent_support_count_invalid"))
            continue
        if not sufficiency_state:
            decisions.append(_abstain(source_ref, "evidence_sufficiency_state_missing"))
            continue
        evidence_profile, evidence_profile_error, profile_reasons = _validated_evidence_profile(
            sufficiency,
            support,
            counterevidence,
        )
        if evidence_profile_error:
            decisions.append(_abstain(source_ref, evidence_profile_error))
            continue
        if not safe_meaning or not forbidden or not withdrawals:
            decisions.append(_abstain(source_ref, "safe_finding_contract_incomplete"))
            continue
        if alternatives_error:
            decisions.append(_abstain(source_ref, alternatives_error))
            continue
        if typed_defeat_error:
            decisions.append(_abstain(source_ref, typed_defeat_error))
            continue

        uncertainty = handoff.get("uncertainty")
        if isinstance(uncertainty, dict) and any(
            uncertainty.get(key) is True
            for key in (
                "no_visible_followup_is_failure",
                "absence_of_evidence_is_counterevidence",
                "robustness_is_tactical_pattern_truth",
                "recurrence_is_tactical_intention_truth",
                "censoring_is_failure",
            )
        ):
            decisions.append(_abstain(source_ref, "uncertainty_truth_lock_breached"))
            continue

        dependency_burden, dependency_burden_reasons = _dependency_burden_profile(
            handoff,
            independent_support=independent_support,
            independence_proven=independence_proven,
            statistical_independence_proven=statistical_independence_proven,
        )
        challenge_visible = bool(counter_refs) or bool(alternatives)
        emit_reasons: list[str] = []
        if blocking:
            emit_reasons.extend(blocking)
        emit_reasons.extend(profile_reasons)
        if independent_support < 1:
            emit_reasons.append("INDEPENDENT_SUPPORT_NOT_ADMITTED")
        if not independence_proven:
            emit_reasons.append("DEPENDENCY_INDEPENDENCE_NOT_PROVEN")
        if not statistical_independence_proven:
            emit_reasons.append("STATISTICAL_INDEPENDENCE_NOT_PROVEN")
        if not independence_proven:
            emit_reasons.extend(dependency_burden_reasons)
        if not challenge_visible:
            emit_reasons.append("CHALLENGE_SURFACE_EMPTY")
        if source_review_unscoped:
            emit_reasons.append("UPSTREAM_COUNTEREVIDENCE_REVIEW_UNSCOPED")
        if typed_defeat_profile.get("observed_defeat_type") == "DEFEAT_TYPE_UNRESOLVED":
            emit_reasons.append("TYPED_DEFEAT_TARGET_UNRESOLVED")

        if not emit_reasons:
            decision = "EMIT"
            claim_output_allowed = True
            claim_ceiling = CLAIM_CEILING_EMIT
        else:
            decision = "DOWNGRADE"
            claim_output_allowed = False
            claim_ceiling = CLAIM_CEILING_DOWNGRADE

        decisions.append({
            "source_safe_finding_handoff_ref": source_ref,
            "decision": decision,
            "decision_reasons": sorted(set(emit_reasons)),
            "claim_output_allowed": claim_output_allowed,
            "claim_ceiling": claim_ceiling,
            "admitted_independent_support_count": independent_support,
            "dependency_independence_proven": independence_proven,
            "statistical_independence_proven": statistical_independence_proven,
            "dependency_burden_profile": dependency_burden,
            "comparable_counterexample_visible": bool(counter_refs),
            "withdrawal_condition_present": bool(withdrawals),
            "typed_defeat_profile": typed_defeat_profile,
            "typed_defeat_target_unresolved": (
                typed_defeat_profile.get("observed_defeat_type") == "DEFEAT_TYPE_UNRESOLVED"
            ),
            "typed_defeat_can_authorize_emit": False,
            "typed_defeat_can_strengthen_claim_ceiling": False,
            "typed_defeat_creates_new_evidence": False,
            "evidence_profile_dimensions_validated": True,
            **(evidence_profile or {}),
        })

    counts = Counter(row.get("decision") for row in decisions)
    emitted = int(counts.get("EMIT", 0))
    abstained = int(counts.get("ABSTAIN", 0))
    if abstained:
        review_hits.append("one_or_more_handoffs_abstained")

    profiled = sum(
        isinstance(row.get("dependency_burden_profile"), dict)
        for row in decisions
        if isinstance(row, dict)
    )
    shared_anchor_dominated = sum(
        (row.get("dependency_burden_profile") or {}).get("profile_state")
        == "SHARED_VISIBLE_ANCHOR_DEPENDENCY_DOMINATED"
        for row in decisions
        if isinstance(row, dict)
    )

    return {
        "status": "REVIEW_REQUIRED" if review_hits else "PASS",
        "safe_finding_admission_decisions": decisions,
        "safe_finding_admission_decision_count": len(decisions),
        "finding_status_counts": {
            "EMIT": emitted,
            "DOWNGRADE": int(counts.get("DOWNGRADE", 0)),
            "ABSTAIN": abstained,
        },
        "professional_finding_emitted_count": emitted,
        "claim_output_allowed_count": emitted,
        "dependency_burden_profiled_decision_count": profiled,
        "shared_anchor_dependency_dominated_decision_count": shared_anchor_dominated,
        "dependency_burden_profile_is_non_compensatory": True,
        "dependency_burden_numeric_score_allowed": False,
        "dependency_burden_can_authorize_independence": False,
        "decision_rows_copy_evidence_payloads": False,
        "decision_projection_creates_new_evidence": False,
        "decision_projection_reconstructs_sequences": False,
        "evidence_profile_dimensions_required_for_emit": True,
        "evidence_profile_dimensions_compensate_each_other": False,
        "review_required_is_not_fail": True,
        "counterevidence_review_scope": counterevidence_review_scope,
        "counterevidence_scoped_review_surface_declared": scoped_review_declared,
        "unscoped_upstream_review_can_authorize_emit": False,
        "pass_with_unscoped_review_hits_can_authorize_emit": False,
        "malformed_alternative_can_satisfy_challenge": False,
        "hard_block_hits": [],
        "review_hits": sorted(set(review_hits)),
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
