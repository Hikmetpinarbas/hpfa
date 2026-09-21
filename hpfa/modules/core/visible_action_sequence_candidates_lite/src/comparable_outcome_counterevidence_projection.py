from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from itertools import combinations
from typing import Any

CLAIM_CEILING = "MATCH_LOCAL_COMPARABLE_VISIBLE_OUTCOME_COUNTEREVIDENCE_CANDIDATE_ONLY"
SAFE_FINDING_HANDOFF_CLAIM_CEILING = "DOWNGRADED_MATCH_LOCAL_SAFE_FINDING_HANDOFF_CANDIDATE_ONLY"
BRANCH_COUNTEREVIDENCE_CLAIM_CEILING = "SAME_DESIGN_BRANCH_VARIATION_AND_CHALLENGE_CANDIDATE_ONLY"
VISIBLE_OUTCOME_STATES = {"SUCCESS_SEMANTIC_VISIBLE", "FAILURE_SEMANTIC_VISIBLE"}
BRANCH_QUESTION_ID = "shared_visible_anchor_branch_contrast_v1"
CANONICAL_EVIDENCE_DIRECTION_CLASSES = {
    "SUPPORT",
    "COUNTEREVIDENCE",
    "NON_SUPPORT",
    "UNRESOLVED",
    "NOT_EVALUATED",
}


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _digest(*values: Any) -> str:
    raw = json.dumps(values, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _variant_sequence_map(payload: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for row in payload.get("partial_order_occurrence_variants") or []:
        if not isinstance(row, dict):
            continue
        variant_id = _clean(row.get("partial_order_occurrence_variant_id"))
        sequence_ref = _clean(row.get("sequence_ref"))
        if variant_id and sequence_ref:
            out[variant_id] = sequence_ref
    return out


def _sequence_outcome_map(payload: dict[str, Any]) -> dict[str, set[str]]:
    out: dict[str, set[str]] = defaultdict(set)
    for divergence in payload.get("first_supported_branch_divergence_candidates") or []:
        if not isinstance(divergence, dict):
            continue
        for branch in divergence.get("branch_profiles") or []:
            if not isinstance(branch, dict):
                continue
            state = _clean(branch.get("branch_outcome_state"))
            if not state:
                continue
            for sequence_ref in branch.get("supporting_visible_sequence_candidate_ids") or []:
                sequence_ref = _clean(sequence_ref)
                if sequence_ref:
                    out[sequence_ref].add(state)
    return out


def _resolved_state(sequence_ref: str, outcomes: dict[str, set[str]]) -> str | None:
    states = outcomes.get(sequence_ref) or set()
    visible = sorted(state for state in states if state in VISIBLE_OUTCOME_STATES)
    return visible[0] if len(visible) == 1 else None


def _branch_sequence_refs(divergence: dict[str, Any], outcome_state: str) -> list[str]:
    refs = {
        _clean(sequence_ref)
        for branch in (divergence.get("branch_profiles") or [])
        if isinstance(branch, dict) and _clean(branch.get("branch_outcome_state")) == outcome_state
        for sequence_ref in (branch.get("supporting_visible_sequence_candidate_ids") or [])
        if _clean(sequence_ref)
    }
    return sorted(refs)


def _explicit_dependency_challenge(pair: dict[str, Any]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if int(pair.get("shared_occurrence_candidate_count") or 0) > 0:
        reasons.append("SHARED_OCCURRENCE_ROOT")
    if int(pair.get("shared_dependency_group_count") or 0) > 0:
        reasons.append("SHARED_DEPENDENCY_GROUP")
    if _clean(pair.get("pair_state")) == "DEPENDENT_SHARED_ORIGIN_VARIANT_PAIR":
        reasons.append("DEPENDENT_SHARED_ORIGIN_PAIR_STATE")
    if _clean(pair.get("comparison_eligibility_state")) == "COMPARABLE_FOR_SHARED_ORIGIN_BRANCH_CONTRAST":
        reasons.append("SHARED_ORIGIN_COMPARISON_DESIGN")
    return bool(reasons), sorted(set(reasons))


def _legacy_evidence_direction(contrast_state: str) -> str:
    mapping = {
        "COMPARABLE_SAME_VISIBLE_OUTCOME": "SUPPORT",
        "COMPARABLE_DIFFERENT_VISIBLE_OUTCOME_COUNTEREXAMPLE_CANDIDATE": "COUNTEREVIDENCE",
        "COMPARABLE_VISIBLE_OUTCOME_SEMANTIC_UNRESOLVED_REVIEW_REQUIRED": "UNRESOLVED",
        "COMPARABLE_VARIANT_SEQUENCE_BINDING_MISSING_REVIEW_REQUIRED": "UNRESOLVED",
        "NOT_APPLICABLE_OR_REVIEW_REQUIRED_COMPARISON": "NOT_EVALUATED",
    }
    return mapping.get(contrast_state, "UNRESOLVED")


def _branch_evidence_direction(
    *,
    same_branch: bool,
    left_outcome: str | None,
    right_outcome: str | None,
) -> tuple[str, str]:
    if left_outcome is None or right_outcome is None:
        return "UNRESOLVED", (
            "WITHIN_BRANCH_VISIBLE_OUTCOME_STABILITY"
            if same_branch
            else "BETWEEN_BRANCH_VISIBLE_OUTCOME_DISCRIMINATION"
        )
    if same_branch:
        if left_outcome == right_outcome:
            return "SUPPORT", "WITHIN_BRANCH_VISIBLE_OUTCOME_STABILITY"
        return "COUNTEREVIDENCE", "WITHIN_BRANCH_VISIBLE_OUTCOME_STABILITY"
    if left_outcome == right_outcome:
        return "NON_SUPPORT", "BETWEEN_BRANCH_VISIBLE_OUTCOME_DISCRIMINATION"
    return "SUPPORT", "BETWEEN_BRANCH_VISIBLE_OUTCOME_DISCRIMINATION"


def _variant_comparable_set_bindings(
    sequence_payload: dict[str, Any],
) -> tuple[dict[str, dict[str, Any]], set[str]]:
    bindings: dict[str, dict[str, Any]] = {}
    ambiguous: set[str] = set()
    for row in sequence_payload.get("process_comparable_sets") or []:
        if not isinstance(row, dict):
            continue
        comparable_set_id = _clean(row.get("comparable_set_id"))
        if not comparable_set_id:
            continue
        eligible_case_count = row.get("eligible_case_count")
        if (
            not isinstance(eligible_case_count, int)
            or isinstance(eligible_case_count, bool)
            or eligible_case_count < 0
        ):
            eligible_case_count = None
        binding = {
            "comparable_set_id": comparable_set_id,
            "comparison_question_id": _clean(row.get("comparison_question_id")) or None,
            "eligible_case_count": eligible_case_count,
            "eligible_denominator_frozen_before_outcome_attachment": (
                row.get("eligible_denominator_frozen_before_outcome_attachment") is True
            ),
            "materialized_pair_count_is_eligible_denominator": (
                row.get("materialized_pair_count_is_eligible_denominator") is True
            ),
        }
        for raw_variant_id in row.get("member_process_candidate_ids") or []:
            variant_id = _clean(raw_variant_id)
            if not variant_id:
                continue
            previous = bindings.get(variant_id)
            if previous and previous.get("comparable_set_id") != comparable_set_id:
                ambiguous.add(variant_id)
                bindings.pop(variant_id, None)
                continue
            if variant_id not in ambiguous:
                bindings[variant_id] = binding
    return bindings, ambiguous


def _legacy_denominator_binding(
    *,
    left_variant: str,
    right_variant: str,
    variant_set_bindings: dict[str, dict[str, Any]],
    ambiguous_variant_ids: set[str],
) -> dict[str, Any]:
    if left_variant in ambiguous_variant_ids or right_variant in ambiguous_variant_ids:
        return {
            "state": "COMPARABLE_SET_MEMBERSHIP_AMBIGUOUS_REVIEW_REQUIRED",
            "comparable_set_id": None,
            "comparison_question_id": None,
            "eligible_case_count": None,
            "frozen": False,
        }
    left = variant_set_bindings.get(left_variant)
    right = variant_set_bindings.get(right_variant)
    if not left or not right:
        return {
            "state": "COMPARABLE_SET_DENOMINATOR_BINDING_UNRESOLVED",
            "comparable_set_id": None,
            "comparison_question_id": None,
            "eligible_case_count": None,
            "frozen": False,
        }
    if left.get("comparable_set_id") != right.get("comparable_set_id"):
        return {
            "state": "PAIR_MEMBERS_DIFFERENT_COMPARABLE_SETS_REVIEW_REQUIRED",
            "comparable_set_id": None,
            "comparison_question_id": None,
            "eligible_case_count": None,
            "frozen": False,
        }
    frozen = left.get("eligible_denominator_frozen_before_outcome_attachment") is True
    pair_not_denominator = left.get("materialized_pair_count_is_eligible_denominator") is False
    count = left.get("eligible_case_count")
    state = (
        "FROZEN_COMPARABLE_SET_ELIGIBLE_CASE_DENOMINATOR_BOUND"
        if frozen and pair_not_denominator and isinstance(count, int)
        else "COMPARABLE_SET_DENOMINATOR_CONTRACT_UNRESOLVED_REVIEW_REQUIRED"
    )
    return {
        "state": state,
        "comparable_set_id": left.get("comparable_set_id"),
        "comparison_question_id": left.get("comparison_question_id"),
        "eligible_case_count": count,
        "frozen": frozen,
    }


def _legacy_similarity_records(
    sequence_payload: dict[str, Any],
    sequence_outcomes: dict[str, set[str]],
    reviews: list[str],
) -> list[dict[str, Any]]:
    variant_to_sequence = _variant_sequence_map(sequence_payload)
    variant_set_bindings, ambiguous_variant_ids = _variant_comparable_set_bindings(sequence_payload)
    records: list[dict[str, Any]] = []
    for pair in sequence_payload.get("dependency_aware_partial_order_similarity_pairs") or []:
        if not isinstance(pair, dict):
            continue
        pair_id = _clean(pair.get("partial_order_similarity_pair_id"))
        left_variant = _clean(pair.get("left_variant_ref"))
        right_variant = _clean(pair.get("right_variant_ref"))
        comparison_state = _clean(pair.get("comparison_eligibility_state"))
        comparison_eligible = pair.get("comparison_eligible") is True

        left_sequence = variant_to_sequence.get(left_variant)
        right_sequence = variant_to_sequence.get(right_variant)
        left_outcome = _resolved_state(left_sequence or "", sequence_outcomes) if left_sequence else None
        right_outcome = _resolved_state(right_sequence or "", sequence_outcomes) if right_sequence else None

        if not comparison_eligible:
            contrast_state = "NOT_APPLICABLE_OR_REVIEW_REQUIRED_COMPARISON"
            candidate = False
        elif not left_sequence or not right_sequence:
            contrast_state = "COMPARABLE_VARIANT_SEQUENCE_BINDING_MISSING_REVIEW_REQUIRED"
            candidate = False
            reviews.append(f"comparable_variant_sequence_binding_missing:{pair_id}")
        elif left_outcome is None or right_outcome is None:
            contrast_state = "COMPARABLE_VISIBLE_OUTCOME_SEMANTIC_UNRESOLVED_REVIEW_REQUIRED"
            candidate = False
            reviews.append(f"comparable_visible_outcome_semantic_unresolved:{pair_id}")
        elif left_outcome == right_outcome:
            contrast_state = "COMPARABLE_SAME_VISIBLE_OUTCOME"
            candidate = False
        else:
            contrast_state = "COMPARABLE_DIFFERENT_VISIBLE_OUTCOME_COUNTEREXAMPLE_CANDIDATE"
            candidate = True

        evidence_direction = _legacy_evidence_direction(contrast_state)
        dependency_challenge_present, dependency_challenge_reasons = _explicit_dependency_challenge(pair)
        denominator_binding = _legacy_denominator_binding(
            left_variant=left_variant,
            right_variant=right_variant,
            variant_set_bindings=variant_set_bindings,
            ambiguous_variant_ids=ambiguous_variant_ids,
        )
        record_id = "coc_" + _digest(pair_id, left_variant, right_variant, left_outcome, right_outcome)[:24]
        records.append({
            "comparable_outcome_counterevidence_id": record_id,
            "counterevidence_design": "RECURRENCE_EXACT_STRUCTURE_COMPATIBILITY_SURFACE",
            "partial_order_similarity_pair_ref": pair_id or None,
            "left_variant_ref": left_variant or None,
            "right_variant_ref": right_variant or None,
            "left_sequence_ref": left_sequence,
            "right_sequence_ref": right_sequence,
            "comparison_eligibility_state": comparison_state or None,
            "comparison_eligible": comparison_eligible,
            "left_visible_outcome_state": left_outcome,
            "right_visible_outcome_state": right_outcome,
            "comparable_outcome_contrast_state": contrast_state,
            "canonical_evidence_direction_class": evidence_direction,
            "canonical_evidence_observation_unit": "COMPARABLE_VARIANT_PAIR_RELATION",
            "canonical_evidence_target_construct": "STRUCTURAL_RECURRENCE_VISIBLE_OUTCOME_CONSISTENCY",
            "canonical_evidence_target_component": "WITHIN_COMPARABLE_SET_VISIBLE_OUTCOME_CONSISTENCY",
            "canonical_evidence_target_question_id": (
                denominator_binding.get("comparison_question_id")
                or _clean(pair.get("comparison_question_id"))
                or None
            ),
            "canonical_evidence_target_comparable_set_id": denominator_binding.get("comparable_set_id"),
            "eligible_denominator_binding_state": denominator_binding.get("state"),
            "eligible_denominator_basis": "FROZEN_COMPARABLE_SET_ELIGIBLE_CASES",
            "eligible_denominator_count": denominator_binding.get("eligible_case_count"),
            "eligible_denominator_frozen_before_outcome_attachment": (
                denominator_binding.get("frozen") is True
            ),
            "pair_record_is_eligible_denominator": False,
            "pair_count_is_eligible_denominator": False,
            "eligible_denominator_is_independent_evidence_count": False,
            "dependency_challenge_present": dependency_challenge_present,
            "dependency_challenge_reason_codes": dependency_challenge_reasons,
            "dependency_challenge_changes_evidence_direction": False,
            "independent_evidence_vote_allowed": False,
            "non_support_is_counterevidence": False,
            "unresolved_is_failure": False,
            "comparable_counterevidence_candidate": candidate,
            "counterevidence_is_independent_support": False,
            "dependency_independence_proven": False,
            "statistical_independence_proven": False,
            "counterevidence_is_causal_refutation": False,
            "outcome_difference_is_failure_cause_truth": False,
            "outcome_difference_is_tactical_pattern_truth": False,
            "absence_is_counterevidence": False,
            "no_visible_followup_is_failure_truth": False,
            "same_timestamp_internal_ordering_allowed": False,
            "source_row_order_is_temporal_truth": False,
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "claim_ceiling": CLAIM_CEILING,
        })
    return records


def _branch_design_records(
    sequence_payload: dict[str, Any],
    sequence_outcomes: dict[str, set[str]],
    reviews: list[str],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for divergence in sequence_payload.get("first_supported_branch_divergence_candidates") or []:
        if not isinstance(divergence, dict):
            continue
        divergence_id = _clean(divergence.get("first_supported_branch_divergence_id"))
        comparable_set_id = _clean(divergence.get("comparable_set_id"))
        question_id = _clean(divergence.get("comparison_question_id"))
        if not divergence_id or not comparable_set_id:
            continue
        if question_id != BRANCH_QUESTION_ID:
            reviews.append(f"branch_counterevidence_question_mismatch:{divergence_id}")
            continue
        if divergence.get("eligible_denominator_frozen_before_divergence_outcome_attachment") is not True:
            reviews.append(f"branch_counterevidence_denominator_not_frozen:{divergence_id}")
            continue
        if divergence.get("outcome_used_in_divergence_location") is not False:
            reviews.append(f"branch_counterevidence_outcome_leakage:{divergence_id}")
            continue

        branch_cases: list[tuple[str, str, str | None]] = []
        for branch in divergence.get("branch_profiles") or []:
            if not isinstance(branch, dict):
                continue
            branch_id = _clean(branch.get("branch_id"))
            if not branch_id:
                continue
            for sequence_ref in branch.get("supporting_visible_sequence_candidate_ids") or []:
                sequence_ref = _clean(sequence_ref)
                if sequence_ref:
                    branch_cases.append((branch_id, sequence_ref, _resolved_state(sequence_ref, sequence_outcomes)))

        for left, right in combinations(sorted(set(branch_cases)), 2):
            left_branch, left_sequence, left_outcome = left
            right_branch, right_sequence, right_outcome = right
            same_branch = left_branch == right_branch
            if left_outcome is None or right_outcome is None:
                state = "SAME_DESIGN_VISIBLE_OUTCOME_UNRESOLVED_REVIEW_REQUIRED"
                challenge = False
                variation = False
                reviews.append(
                    f"same_design_visible_outcome_unresolved:{divergence_id}:{left_sequence}:{right_sequence}"
                )
            elif same_branch and left_outcome != right_outcome:
                state = "SAME_BRANCH_DIFFERENT_VISIBLE_OUTCOME_CHALLENGE_CANDIDATE"
                challenge = True
                variation = True
            elif same_branch:
                state = "SAME_BRANCH_SAME_VISIBLE_OUTCOME"
                challenge = False
                variation = False
            elif left_outcome == right_outcome:
                state = "SAME_PREFIX_DIFFERENT_BRANCH_SAME_VISIBLE_OUTCOME_CHALLENGE_CANDIDATE"
                challenge = True
                variation = False
            else:
                state = "SAME_PREFIX_DIFFERENT_BRANCH_DIFFERENT_VISIBLE_OUTCOME_VARIATION_CANDIDATE"
                challenge = False
                variation = True

            canonical_evidence_direction, canonical_target_component = _branch_evidence_direction(
                same_branch=same_branch,
                left_outcome=left_outcome,
                right_outcome=right_outcome,
            )
            branch_denominator = divergence.get("observed_branch_opportunity_eligible_denominator")
            if (
                not isinstance(branch_denominator, int)
                or isinstance(branch_denominator, bool)
                or branch_denominator < 0
            ):
                branch_denominator = None
            branch_denominator_state = (
                "FROZEN_BRANCH_ELIGIBLE_CASE_DENOMINATOR_BOUND"
                if branch_denominator is not None
                else "BRANCH_ELIGIBLE_CASE_DENOMINATOR_UNRESOLVED_REVIEW_REQUIRED"
            )

            record_id = "boc_" + _digest(
                comparable_set_id,
                divergence_id,
                left_branch,
                right_branch,
                left_sequence,
                right_sequence,
                left_outcome,
                right_outcome,
            )[:24]
            records.append({
                "branch_comparison_counterevidence_id": record_id,
                "counterevidence_design": "SAME_DECLARED_BRANCH_COMPARISON_DESIGN",
                "comparison_question_id": question_id,
                "comparable_set_id": comparable_set_id,
                "source_first_supported_branch_divergence_ref": divergence_id,
                "left_branch_id": left_branch,
                "right_branch_id": right_branch,
                "same_branch": same_branch,
                "left_sequence_ref": left_sequence,
                "right_sequence_ref": right_sequence,
                "left_visible_outcome_state": left_outcome,
                "right_visible_outcome_state": right_outcome,
                "branch_comparison_contrast_state": state,
                "canonical_evidence_direction_class": canonical_evidence_direction,
                "canonical_evidence_observation_unit": "SAME_DESIGN_BRANCH_CASE_PAIR_RELATION",
                "canonical_evidence_target_construct": "BRANCH_OUTCOME_STABILITY_AND_DISCRIMINATION",
                "canonical_evidence_target_component": canonical_target_component,
                "canonical_evidence_target_question_id": question_id,
                "canonical_evidence_target_comparable_set_id": comparable_set_id,
                "eligible_denominator_binding_state": branch_denominator_state,
                "eligible_denominator_basis": "FROZEN_ELIGIBLE_CASES_FROM_FIRST_SUPPORTED_BRANCH_DIVERGENCE",
                "eligible_denominator_count": branch_denominator,
                "eligible_denominator_frozen_before_outcome_attachment": True,
                "pair_record_is_eligible_denominator": False,
                "pair_count_is_eligible_denominator": False,
                "eligible_denominator_is_independent_evidence_count": False,
                "dependency_challenge_present": None,
                "dependency_challenge_state": "NOT_EVALUATED_IN_BRANCH_RECORD",
                "dependency_challenge_changes_evidence_direction": False,
                "independent_evidence_vote_allowed": False,
                "non_support_is_counterevidence": False,
                "unresolved_is_failure": False,
                "same_design_challenge_candidate": challenge,
                "same_design_variation_candidate": variation,
                "comparison_eligible": True,
                "eligible_denominator_frozen_before_outcome_attachment": True,
                "outcome_used_in_comparison_admission": False,
                "outcome_used_in_divergence_location": False,
                "counterevidence_is_independent_support": False,
                "counterevidence_is_causal_refutation": False,
                "outcome_difference_is_failure_cause_truth": False,
                "outcome_difference_is_tactical_pattern_truth": False,
                "absence_is_counterevidence": False,
                "no_visible_followup_is_failure_truth": False,
                "canonical_event_count": "UNKNOWN",
                "true_action_count": "UNKNOWN",
                "production_release": False,
                "claim_ceiling": BRANCH_COUNTEREVIDENCE_CLAIM_CEILING,
            })
    return records


def _evidence_sufficiency_profile(
    divergence: dict[str, Any],
    *,
    denominator: int,
    independent_support: int,
    independence_proven: bool,
    statistical_independence_proven: bool,
    episode_spread: Any,
    context_state: str,
    counterexample_pair_count: int,
) -> dict[str, Any]:
    actor_spread = divergence.get("observed_branch_opportunity_actor_spread_count", "UNKNOWN")
    visible_branch_count = divergence.get("observed_branch_opportunity_total_visible_branch_count", "UNKNOWN")
    success_n = divergence.get("observed_branch_opportunity_success_numerator", 0)
    failure_n = divergence.get("observed_branch_opportunity_failure_numerator", 0)
    unresolved_n = divergence.get("observed_branch_opportunity_unresolved_numerator", 0)
    success_n = success_n if isinstance(success_n, int) and not isinstance(success_n, bool) and success_n >= 0 else 0
    failure_n = failure_n if isinstance(failure_n, int) and not isinstance(failure_n, bool) and failure_n >= 0 else 0
    unresolved_n = unresolved_n if isinstance(unresolved_n, int) and not isinstance(unresolved_n, bool) and unresolved_n >= 0 else 0
    resolved_n = success_n + failure_n
    accounted_n = resolved_n + unresolved_n

    if denominator >= 0 and accounted_n == denominator:
        if unresolved_n:
            case_coverage_state = "COMPLETE_CASE_ACCOUNTING_WITH_UNRESOLVED_OUTCOMES"
        else:
            case_coverage_state = "COMPLETE_RESOLVED_CASE_COVERAGE"
    elif denominator >= 0 and accounted_n < denominator:
        case_coverage_state = "PARTIAL_ELIGIBLE_CASE_ACCOUNTING"
    else:
        case_coverage_state = "ELIGIBLE_CASE_ACCOUNTING_INCONSISTENT"

    if isinstance(visible_branch_count, int) and not isinstance(visible_branch_count, bool):
        legacy_unresolved_visible = max(visible_branch_count - denominator, 0)
        legacy_branch_state = (
            "COMPLETE_FOR_VISIBLE_BRANCHES"
            if visible_branch_count == denominator
            else "PARTIAL_VISIBLE_OUTCOME_COVERAGE"
        )
    else:
        legacy_unresolved_visible = "UNKNOWN"
        legacy_branch_state = "VISIBLE_OUTCOME_COVERAGE_UNKNOWN"

    blocking_dimensions: list[str] = []
    if independent_support < 1:
        blocking_dimensions.append("INDEPENDENT_SUPPORT_NOT_ADMITTED")
    if not independence_proven:
        blocking_dimensions.append("DEPENDENCY_INDEPENDENCE_NOT_PROVEN")
    if not statistical_independence_proven:
        blocking_dimensions.append("STATISTICAL_INDEPENDENCE_NOT_PROVEN")
    if episode_spread == "UNKNOWN":
        blocking_dimensions.append("EPISODE_SPREAD_UNKNOWN")
    if context_state != "COMPLETE":
        blocking_dimensions.append("CONTEXT_COVERAGE_PARTIAL_OR_UNKNOWN")
    if case_coverage_state != "COMPLETE_RESOLVED_CASE_COVERAGE":
        blocking_dimensions.append("OUTCOME_COVERAGE_PARTIAL_OR_UNKNOWN")
    if isinstance(actor_spread, int) and not isinstance(actor_spread, bool) and actor_spread <= 1:
        blocking_dimensions.append("SINGLE_ACTOR_CONCENTRATION")
    elif actor_spread == "UNKNOWN":
        blocking_dimensions.append("ACTOR_SPREAD_UNKNOWN")
    if counterexample_pair_count < 1:
        blocking_dimensions.append("CHALLENGE_SURFACE_EMPTY")

    return {
        "state": (
            "INSUFFICIENT_FOR_PROFESSIONAL_EMIT"
            if blocking_dimensions
            else "NO_BLOCKING_DIMENSION_VISIBLE_BUT_EMIT_NOT_AUTHORIZED_HERE"
        ),
        "blocking_dimensions": sorted(set(blocking_dimensions)),
        "dimensions": {
            "independent_support": {
                "admitted_count": independent_support,
                "dependency_independence_proven": independence_proven,
                "statistical_independence_proven": statistical_independence_proven,
            },
            "outcome_coverage": {
                "eligible_resolved_branch_count": denominator,
                "total_visible_branch_count": visible_branch_count,
                "unresolved_visible_branch_count": legacy_unresolved_visible,
                "state": legacy_branch_state,
                "legacy_branch_shape_descriptor_only": True,
            },
            "eligible_case_coverage": {
                "eligible_case_count": denominator,
                "resolved_outcome_case_count": resolved_n,
                "unresolved_outcome_case_count": unresolved_n,
                "accounted_case_count": accounted_n,
                "state": case_coverage_state,
                "coverage_unit": "FROZEN_ELIGIBLE_CASE",
            },
            "branch_shape": {
                "total_visible_branch_count": visible_branch_count,
                "branch_count_is_case_denominator": False,
            },
            "episode_spread": {
                "count": episode_spread,
                "state": "UNKNOWN" if episode_spread == "UNKNOWN" else "OBSERVED",
            },
            "context_coverage": {"state": context_state},
            "actor_spread": {
                "count": actor_spread,
                "single_actor_concentration": (
                    actor_spread <= 1
                    if isinstance(actor_spread, int) and not isinstance(actor_spread, bool)
                    else "UNKNOWN"
                ),
            },
            "challenge_surface": {
                "comparable_counterexample_pair_count": counterexample_pair_count,
                "pair_count_is_independent_evidence_count": False,
                "independent_counterevidence_support_count": 0,
            },
        },
        "numeric_sufficiency_score": None,
        "universal_sufficiency_threshold_used": False,
        "dimensions_compensate_each_other": False,
        "missing_dimension_is_zero": False,
        "coverage_is_generalizability_truth": False,
        "high_raw_rate_can_override_dependency_block": False,
        "counterexample_pair_count_can_override_independence_block": False,
        "claim_strengthened_by_profile": False,
    }


def _typed_defeat_contract(
    *,
    handoff_id: str,
    divergence_id: str,
    comparable_set_id: str,
    challenge_refs: list[str],
    withdrawal_conditions: list[str],
) -> dict[str, Any]:
    """Expose attack-target debt and typed conditional withdrawal rules.

    Observed counterexamples are not automatically REBUT attacks because the current
    Safe Finding conclusion is itself a bounded variation cue. Without an explicit
    target claim component, the active defeat type remains unresolved.
    """
    target_for_premise = divergence_id or handoff_id
    target_for_warrant = comparable_set_id or divergence_id or handoff_id
    rule_specs = {
        "WITHDRAW_IF_SHARED_ANCHOR_ADMISSION_INVALIDATED": (
            "UNDERMINE",
            "SUPPORTING_PREMISE",
            target_for_premise,
            "ABSTAIN",
        ),
        "WITHDRAW_IF_OUTCOME_SEMANTIC_BINDING_INVALIDATED": (
            "UNDERMINE",
            "SUPPORTING_PREMISE",
            target_for_premise,
            "ABSTAIN",
        ),
        "WITHDRAW_IF_COMPARISON_ELIGIBILITY_INVALIDATED": (
            "UNDERCUT",
            "INFERENCE_WARRANT",
            target_for_warrant,
            "ABSTAIN",
        ),
        "WITHDRAW_IF_SAME_DESIGN_COUNTEREVIDENCE_BINDING_INVALIDATED": (
            "UNDERCUT",
            "CHALLENGE_BINDING_WARRANT",
            target_for_warrant,
            "REVIEW_REQUIRED",
        ),
        "WITHDRAW_IF_COMPARABLE_COUNTEREXAMPLE_BINDING_DISAPPEARS": (
            "UNDERCUT",
            "CHALLENGE_BINDING_WARRANT",
            handoff_id,
            "REVIEW_REQUIRED",
        ),
    }
    rules: list[dict[str, Any]] = []
    for condition in withdrawal_conditions:
        spec = rule_specs.get(condition)
        if not spec:
            rules.append({
                "condition_code": condition,
                "defeat_type": "DEFEAT_TYPE_UNRESOLVED",
                "target_component_type": "UNRESOLVED",
                "target_component_ref": None,
                "withdrawal_effect": "REVIEW_REQUIRED",
            })
            continue
        defeat_type, component_type, component_ref, effect = spec
        rules.append({
            "condition_code": condition,
            "defeat_type": defeat_type,
            "target_component_type": component_type,
            "target_component_ref": component_ref,
            "withdrawal_effect": effect,
        })

    observed_state = (
        "UNRESOLVED_NO_EXPLICIT_CLAIM_COMPONENT_TARGET"
        if challenge_refs
        else "NOT_APPLICABLE_NO_OBSERVED_COUNTEREXAMPLE"
    )
    return {
        "observed_defeat_state": observed_state,
        "observed_defeat_type": "DEFEAT_TYPE_UNRESOLVED" if challenge_refs else "NOT_APPLICABLE",
        "observed_target_component_type": None,
        "observed_target_component_ref": None,
        "observed_source_counterevidence_refs": sorted(set(challenge_refs)),
        "conditional_withdrawal_rules": rules,
        "defeat_is_causal_refutation": False,
        "defeat_is_independent_support": False,
        "defeat_creates_new_evidence": False,
        "defeat_can_authorize_emit": False,
        "defeat_can_strengthen_claim_ceiling": False,
        "withdrawal_effect_can_strengthen_claim": False,
        "rebut_without_explicit_target_allowed": False,
    }


def _safe_finding_handoff_candidates(
    sequence_payload: dict[str, Any],
    legacy_records: list[dict[str, Any]],
    branch_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    handoffs: list[dict[str, Any]] = []
    for divergence in sequence_payload.get("first_supported_branch_divergence_candidates") or []:
        if not isinstance(divergence, dict):
            continue
        divergence_id = _clean(divergence.get("first_supported_branch_divergence_id"))
        success_refs = _branch_sequence_refs(divergence, "SUCCESS_SEMANTIC_VISIBLE")
        failure_refs = _branch_sequence_refs(divergence, "FAILURE_SEMANTIC_VISIBLE")
        eligible_refs = set(success_refs) | set(failure_refs)
        if not divergence_id or not success_refs or not failure_refs:
            continue

        comparable_set_id = _clean(divergence.get("comparable_set_id"))
        question_id = _clean(divergence.get("comparison_question_id"))
        same_design = bool(comparable_set_id and question_id == BRANCH_QUESTION_ID)

        if same_design:
            design_rows = [
                row
                for row in branch_records
                if _clean(row.get("source_first_supported_branch_divergence_ref")) == divergence_id
                and _clean(row.get("comparable_set_id")) == comparable_set_id
            ]
            challenge_refs = sorted(
                _clean(row.get("branch_comparison_counterevidence_id"))
                for row in design_rows
                if row.get("same_design_challenge_candidate") is True
                and _clean(row.get("branch_comparison_counterevidence_id"))
            )
            variation_refs = sorted(
                _clean(row.get("branch_comparison_counterevidence_id"))
                for row in design_rows
                if row.get("same_design_variation_candidate") is True
                and _clean(row.get("branch_comparison_counterevidence_id"))
            )
            same_outcome_refs = sorted(
                _clean(row.get("branch_comparison_counterevidence_id"))
                for row in design_rows
                if _clean(row.get("branch_comparison_contrast_state"))
                in {
                    "SAME_BRANCH_SAME_VISIBLE_OUTCOME",
                    "SAME_PREFIX_DIFFERENT_BRANCH_SAME_VISIBLE_OUTCOME_CHALLENGE_CANDIDATE",
                }
                and _clean(row.get("branch_comparison_counterevidence_id"))
            )
            counterevidence_design = "SAME_DECLARED_BRANCH_COMPARISON_DESIGN"
        else:
            challenge_refs = sorted(
                _clean(row.get("comparable_outcome_counterevidence_id"))
                for row in legacy_records
                if row.get("comparable_counterevidence_candidate") is True
                and _clean(row.get("left_sequence_ref")) in eligible_refs
                and _clean(row.get("right_sequence_ref")) in eligible_refs
                and _clean(row.get("comparable_outcome_counterevidence_id"))
            )
            variation_refs = list(challenge_refs)
            same_outcome_refs = sorted(
                _clean(row.get("comparable_outcome_counterevidence_id"))
                for row in legacy_records
                if _clean(row.get("comparable_outcome_contrast_state")) == "COMPARABLE_SAME_VISIBLE_OUTCOME"
                and _clean(row.get("left_sequence_ref")) in eligible_refs
                and _clean(row.get("right_sequence_ref")) in eligible_refs
                and _clean(row.get("comparable_outcome_counterevidence_id"))
            )
            counterevidence_design = "LEGACY_RECURRENCE_COMPATIBILITY_FALLBACK"
            if not challenge_refs:
                continue

        numerator = divergence.get("observed_branch_opportunity_success_numerator")
        denominator = divergence.get("observed_branch_opportunity_eligible_denominator")
        raw_rate = divergence.get("observed_branch_opportunity_raw_success_rate")
        if not isinstance(numerator, int) or isinstance(numerator, bool):
            numerator = len(success_refs)
        if not isinstance(denominator, int) or isinstance(denominator, bool):
            denominator = len(success_refs) + len(failure_refs)
        if raw_rate is None and denominator:
            raw_rate = round(numerator / denominator, 6)

        independent_support = divergence.get(
            "observed_branch_opportunity_admitted_independent_support_count", 0
        )
        if (
            not isinstance(independent_support, int)
            or isinstance(independent_support, bool)
            or independent_support < 0
        ):
            independent_support = 0
        independence_proven = (
            divergence.get("observed_branch_opportunity_dependency_independence_proven") is True
        )
        statistical_independence_proven = (
            divergence.get("observed_branch_opportunity_statistical_independence_proven") is True
        )
        episode_spread = divergence.get("observed_branch_opportunity_episode_spread_count", "UNKNOWN")
        context_state = (
            _clean(divergence.get("observed_branch_opportunity_context_spread_state")) or "UNKNOWN"
        )
        support_state = (
            _clean(divergence.get("observed_branch_opportunity_support_state")) or "UNKNOWN"
        )
        concentration_warnings = sorted(
            {
                _clean(value)
                for value in (
                    divergence.get("observed_branch_opportunity_concentration_warnings") or []
                )
                if _clean(value)
            }
        )

        evidence_sufficiency = _evidence_sufficiency_profile(
            divergence,
            denominator=denominator,
            independent_support=independent_support,
            independence_proven=independence_proven,
            statistical_independence_proven=statistical_independence_proven,
            episode_spread=episode_spread,
            context_state=context_state,
            counterexample_pair_count=len(challenge_refs),
        )
        downgrade_reasons = [
            "INDEPENDENT_SUPPORT_NOT_ADMITTED",
            "DEPENDENCY_INDEPENDENCE_NOT_PROVEN",
            "STATISTICAL_INDEPENDENCE_NOT_PROVEN",
            "MATCH_LOCAL_SHARED_ANCHOR_ONLY",
        ]
        if episode_spread == "UNKNOWN":
            downgrade_reasons.append("EPISODE_SPREAD_UNKNOWN")
        if context_state != "COMPLETE":
            downgrade_reasons.append("CONTEXT_COVERAGE_PARTIAL_OR_UNKNOWN")
        downgrade_reasons.extend(evidence_sufficiency["blocking_dimensions"])

        handoff_id = "sfh_" + _digest(
            divergence_id,
            comparable_set_id or None,
            success_refs,
            failure_refs,
            challenge_refs,
            variation_refs,
        )[:24]
        withdrawal_conditions = [
            "WITHDRAW_IF_SHARED_ANCHOR_ADMISSION_INVALIDATED",
            "WITHDRAW_IF_OUTCOME_SEMANTIC_BINDING_INVALIDATED",
            "WITHDRAW_IF_COMPARISON_ELIGIBILITY_INVALIDATED",
        ] + (
            ["WITHDRAW_IF_SAME_DESIGN_COUNTEREVIDENCE_BINDING_INVALIDATED"]
            if same_design
            else ["WITHDRAW_IF_COMPARABLE_COUNTEREXAMPLE_BINDING_DISAPPEARS"]
        )
        typed_defeat_contract = _typed_defeat_contract(
            handoff_id=handoff_id,
            divergence_id=divergence_id,
            comparable_set_id=comparable_set_id,
            challenge_refs=challenge_refs,
            withdrawal_conditions=withdrawal_conditions,
        )

        handoffs.append({
            "safe_finding_handoff_candidate_id": handoff_id,
            "source_first_supported_branch_divergence_ref": divergence_id,
            "source_comparable_set_id": comparable_set_id or None,
            "source_comparison_question_id": question_id or None,
            "counterevidence_design": counterevidence_design,
            "same_comparison_design_counterevidence_required": same_design,
            "finding_status": "DOWNGRADE",
            "professional_finding_emit_allowed": False,
            "finding_status_reasons": sorted(set(downgrade_reasons)),
            "what_visible": {
                "state": "SHARED_VISIBLE_ANCHOR_WITH_SUCCESS_FAILURE_SEMANTIC_VARIATION",
                "success_branch_count": len(success_refs),
                "failure_branch_count": len(failure_refs),
                "eligible_outcome_branch_count": denominator,
                "raw_success_rate": raw_rate,
            },
            "where_when": {
                "team_identity_candidate_id": divergence.get("team_identity_candidate_id"),
                "period_candidate": divergence.get("period_candidate"),
                "shared_anchor_time_layer_ref": divergence.get("shared_anchor_time_layer_ref"),
                "shared_anchor_time_candidate": divergence.get("shared_anchor_time_candidate"),
                "anchor_centered_sequence_branch_map_ref": divergence.get(
                    "anchor_centered_sequence_branch_map_ref"
                ),
            },
            "support": {
                "visible_success_sequence_refs": success_refs,
                "visible_success_numerator": numerator,
                "eligible_denominator": denominator,
                "raw_success_rate": raw_rate,
                "support_state": support_state,
                "admitted_independent_support_count": independent_support,
                "dependency_independence_proven": independence_proven,
                "statistical_independence_proven": statistical_independence_proven,
            },
            "counterevidence": {
                "visible_failure_sequence_refs": failure_refs,
                "comparable_counterexample_refs": challenge_refs,
                "comparable_counterexample_pair_count": len(challenge_refs),
                "same_design_variation_refs": variation_refs,
                "same_design_variation_pair_count": len(variation_refs),
                "same_visible_outcome_pair_refs": same_outcome_refs,
                "counterexample_pair_count_is_independent_evidence_count": False,
                "independent_counterevidence_support_count": 0,
                "challenge_surface_empty": len(challenge_refs) == 0,
                "absence_used_as_counterevidence": False,
            },
            "evidence_sufficiency": evidence_sufficiency,
            "alternative_explanations": [
                {
                    "code": "SHARED_ANCHOR_DEPENDENCY",
                    "meaning": "Visible branches share one admitted anchor and are not independent recurrence support.",
                },
                {
                    "code": "PROVIDER_OUTCOME_SEMANTIC_ONLY",
                    "meaning": "SUCCESS/FAILURE are admitted visible outcome semantics, not tactical success truth.",
                },
                {
                    "code": "PARTIAL_CONTEXT_COVERAGE",
                    "meaning": "Match-local context coverage is incomplete for general process claims.",
                },
            ],
            "safe_meaning": "MATCH_LOCAL_SHARED_ANCHOR_VISIBLE_OUTCOME_VARIATION_ONLY",
            "forbidden_inference": [
                "TRUE_SUCCESS_PROBABILITY",
                "INTRINSIC_PROCESS_EFFICIENCY",
                "INDEPENDENT_RECURRENCE_SUPPORT",
                "TACTICAL_PATTERN_TRUTH",
                "COACH_INTENTION",
                "FAILURE_CAUSE",
                "CAUSALITY",
            ],
            "uncertainty": {
                "independent_support_count": independent_support,
                "dependency_independence_proven": independence_proven,
                "statistical_independence_proven": statistical_independence_proven,
                "episode_spread_count": episode_spread,
                "actor_spread_count": divergence.get(
                    "observed_branch_opportunity_actor_spread_count", "UNKNOWN"
                ),
                "context_spread_state": context_state,
                "concentration_warnings": concentration_warnings,
                "binomial_interval_allowed": False,
                "shrinkage_allowed": False,
            },
            "withdrawal_conditions": withdrawal_conditions,
            "typed_defeat_contract": typed_defeat_contract,
            "analyst_action": "REVIEW_BRANCH_EXAMPLES_AND_USE_ONLY_AS_MATCH_LOCAL_VARIATION_CUE",
            "analyst_summary_tr": (
                f"Aynı görünür başlangıçtan çıkan {denominator} uygun vakanın {numerator}'sinde SUCCESS, "
                f"{len(failure_refs)}'inde FAILURE semantiği görüldü; bağımsız tekrar kanıtlanmadığı için bu oran "
                "gerçek başarı olasılığı veya taktik kalite değildir."
            ),
            "safe_finding_handoff_is_professional_finding_truth": False,
            "safe_finding_handoff_is_tactical_truth": False,
            "safe_finding_handoff_is_causal_truth": False,
            "safe_finding_handoff_is_coach_intention_truth": False,
            "same_timestamp_internal_ordering_allowed": False,
            "source_row_order_is_temporal_truth": False,
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
            "claim_ceiling": SAFE_FINDING_HANDOFF_CLAIM_CEILING,
        })
    return handoffs


def build_comparable_outcome_counterevidence(sequence_payload: dict[str, Any]) -> dict[str, Any]:
    blocks: list[str] = []
    reviews: list[str] = []

    if sequence_payload.get("dependency_aware_partial_order_similarity_status") == "FAIL_CLOSED":
        blocks.append("comparison_projection_fail_closed")
    if sequence_payload.get("first_supported_branch_divergence_status") == "FAIL_CLOSED":
        blocks.append("divergence_projection_fail_closed")
    if sequence_payload.get("same_timestamp_internal_ordering_allowed") is not False:
        blocks.append("same_timestamp_internal_ordering_policy_breached")
    if sequence_payload.get("source_row_order_is_temporal_truth") is not False:
        blocks.append("source_row_order_temporal_policy_breached")
    if sequence_payload.get("canonical_event_count") != "UNKNOWN":
        blocks.append("canonical_event_count_claimed")
    if sequence_payload.get("true_action_count") != "UNKNOWN":
        blocks.append("true_action_count_claimed")
    if sequence_payload.get("production_release") is True:
        blocks.append("production_release_claimed")

    sequence_outcomes = _sequence_outcome_map(sequence_payload)
    legacy_records = _legacy_similarity_records(sequence_payload, sequence_outcomes, reviews)
    branch_records = _branch_design_records(sequence_payload, sequence_outcomes, reviews)
    handoffs = (
        _safe_finding_handoff_candidates(sequence_payload, legacy_records, branch_records)
        if not blocks
        else []
    )

    if blocks:
        status = "FAIL_CLOSED"
    elif (
        reviews
        or sequence_payload.get("dependency_aware_partial_order_similarity_status") == "REVIEW_REQUIRED"
        or sequence_payload.get("first_supported_branch_divergence_status") == "REVIEW_REQUIRED"
    ):
        status = "REVIEW_REQUIRED"
    else:
        status = "PASS"

    legacy_counts = Counter(
        _clean(row.get("comparable_outcome_contrast_state")) for row in legacy_records
    )
    branch_counts = Counter(
        _clean(row.get("branch_comparison_contrast_state")) for row in branch_records
    )
    legacy_evidence_direction_counts = Counter(
        _clean(row.get("canonical_evidence_direction_class")) for row in legacy_records
    )
    branch_evidence_direction_counts = Counter(
        _clean(row.get("canonical_evidence_direction_class")) for row in branch_records
    )
    legacy_denominator_binding_counts = Counter(
        _clean(row.get("eligible_denominator_binding_state")) for row in legacy_records
    )
    branch_denominator_binding_counts = Counter(
        _clean(row.get("eligible_denominator_binding_state")) for row in branch_records
    )
    return {
        "status": status,
        "comparable_outcome_counterevidence_records": legacy_records if not blocks else [],
        "comparable_outcome_counterevidence_record_count": len(legacy_records) if not blocks else 0,
        "comparable_outcome_contrast_state_counts": (
            dict(sorted(legacy_counts.items())) if not blocks else {}
        ),
        "comparison_eligible_record_count": (
            sum(1 for row in legacy_records if row.get("comparison_eligible")) if not blocks else 0
        ),
        "comparable_counterevidence_candidate_count": (
            sum(1 for row in legacy_records if row.get("comparable_counterevidence_candidate"))
            if not blocks
            else 0
        ),
        "legacy_similarity_counterevidence_records_are_recurrence_support_surface": True,
        "legacy_similarity_counterevidence_drives_branch_safe_finding_only_as_fallback": True,
        "branch_comparison_counterevidence_records": branch_records if not blocks else [],
        "branch_comparison_counterevidence_record_count": len(branch_records) if not blocks else 0,
        "branch_comparison_contrast_state_counts": (
            dict(sorted(branch_counts.items())) if not blocks else {}
        ),
        "branch_comparison_same_design_challenge_candidate_count": (
            sum(1 for row in branch_records if row.get("same_design_challenge_candidate"))
            if not blocks
            else 0
        ),
        "branch_comparison_same_design_variation_candidate_count": (
            sum(1 for row in branch_records if row.get("same_design_variation_candidate"))
            if not blocks
            else 0
        ),
        "canonical_evidence_classification_applied": True,
        "canonical_evidence_direction_classes": sorted(CANONICAL_EVIDENCE_DIRECTION_CLASSES),
        "legacy_canonical_evidence_direction_counts": (
            dict(sorted(legacy_evidence_direction_counts.items())) if not blocks else {}
        ),
        "branch_canonical_evidence_direction_counts": (
            dict(sorted(branch_evidence_direction_counts.items())) if not blocks else {}
        ),
        "legacy_dependency_challenge_record_count": (
            sum(1 for row in legacy_records if row.get("dependency_challenge_present") is True)
            if not blocks
            else 0
        ),
        "claim_target_denominator_binding_applied": True,
        "legacy_denominator_binding_state_counts": (
            dict(sorted(legacy_denominator_binding_counts.items())) if not blocks else {}
        ),
        "branch_denominator_binding_state_counts": (
            dict(sorted(branch_denominator_binding_counts.items())) if not blocks else {}
        ),
        "pair_record_is_eligible_denominator": False,
        "pair_count_is_eligible_denominator": False,
        "eligible_denominator_is_independent_evidence_count": False,
        "dependency_challenge_is_evidence_direction": False,
        "dependency_challenge_changes_evidence_direction": False,
        "non_support_is_counterevidence": False,
        "unresolved_is_failure": False,
        "safe_finding_counterevidence_uses_same_comparison_design_when_available": True,
        "eligible_denominator_coverage_unit": "FROZEN_ELIGIBLE_CASE",
        "visible_branch_count_is_case_denominator": False,
        "counterevidence_independent_support_count": 0,
        "counterevidence_is_independent_support": False,
        "dependency_independence_proven": False,
        "statistical_independence_proven": False,
        "outcome_difference_is_failure_cause_truth": False,
        "outcome_difference_is_tactical_pattern_truth": False,
        "absence_is_counterevidence": False,
        "no_visible_followup_is_failure_truth": False,
        "safe_finding_handoff_candidates": handoffs,
        "safe_finding_handoff_candidate_count": len(handoffs),
        "safe_finding_handoff_finding_status_counts": {
            "EMIT": 0,
            "DOWNGRADE": len(handoffs),
            "ABSTAIN": 0,
        },
        "professional_finding_emitted_count": 0,
        "safe_finding_handoff_professional_emit_allowed": False,
        "counterexample_pair_count_is_independent_evidence_count": False,
        "safe_finding_handoff_claim_ceiling": SAFE_FINDING_HANDOFF_CLAIM_CEILING,
        "evidence_sufficiency_profile_is_non_compensatory": True,
        "evidence_sufficiency_numeric_score_allowed": False,
        "evidence_sufficiency_universal_threshold_allowed": False,
        "same_timestamp_internal_ordering_allowed": False,
        "source_row_order_is_temporal_truth": False,
        "hard_block_hits": sorted(set(blocks)),
        "review_hits": sorted(set(reviews)),
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
    }
