from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from typing import Any

CLAIM_CEILING = "MATCH_LOCAL_COMPARABLE_VISIBLE_OUTCOME_COUNTEREVIDENCE_CANDIDATE_ONLY"
SAFE_FINDING_HANDOFF_CLAIM_CEILING = "DOWNGRADED_MATCH_LOCAL_SAFE_FINDING_HANDOFF_CANDIDATE_ONLY"
VISIBLE_OUTCOME_STATES = {"SUCCESS_SEMANTIC_VISIBLE", "FAILURE_SEMANTIC_VISIBLE"}


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


def _safe_finding_handoff_candidates(
    sequence_payload: dict[str, Any],
    records: list[dict[str, Any]],
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

        comparable_counterexample_refs = sorted(
            _clean(row.get("comparable_outcome_counterevidence_id"))
            for row in records
            if row.get("comparable_counterevidence_candidate") is True
            and _clean(row.get("left_sequence_ref")) in eligible_refs
            and _clean(row.get("right_sequence_ref")) in eligible_refs
            and _clean(row.get("comparable_outcome_counterevidence_id"))
        )
        same_outcome_refs = sorted(
            _clean(row.get("comparable_outcome_counterevidence_id"))
            for row in records
            if _clean(row.get("comparable_outcome_contrast_state")) == "COMPARABLE_SAME_VISIBLE_OUTCOME"
            and _clean(row.get("left_sequence_ref")) in eligible_refs
            and _clean(row.get("right_sequence_ref")) in eligible_refs
            and _clean(row.get("comparable_outcome_counterevidence_id"))
        )
        if not comparable_counterexample_refs:
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

        independent_support = divergence.get("observed_branch_opportunity_admitted_independent_support_count", 0)
        if not isinstance(independent_support, int) or isinstance(independent_support, bool) or independent_support < 0:
            independent_support = 0
        independence_proven = divergence.get("observed_branch_opportunity_dependency_independence_proven") is True
        statistical_independence_proven = divergence.get(
            "observed_branch_opportunity_statistical_independence_proven"
        ) is True
        episode_spread = divergence.get("observed_branch_opportunity_episode_spread_count", "UNKNOWN")
        context_state = _clean(divergence.get("observed_branch_opportunity_context_spread_state")) or "UNKNOWN"
        support_state = _clean(divergence.get("observed_branch_opportunity_support_state")) or "UNKNOWN"
        concentration_warnings = sorted(
            {_clean(value) for value in (divergence.get("observed_branch_opportunity_concentration_warnings") or []) if _clean(value)}
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

        counterexample_pair_count = len(comparable_counterexample_refs)
        handoff_id = "sfh_" + _digest(
            divergence_id,
            success_refs,
            failure_refs,
            comparable_counterexample_refs,
        )[:24]
        handoffs.append({
            "safe_finding_handoff_candidate_id": handoff_id,
            "source_first_supported_branch_divergence_ref": divergence_id,
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
                "comparable_counterexample_refs": comparable_counterexample_refs,
                "comparable_counterexample_pair_count": counterexample_pair_count,
                "same_visible_outcome_pair_refs": same_outcome_refs,
                "counterexample_pair_count_is_independent_evidence_count": False,
                "independent_counterevidence_support_count": 0,
                "absence_used_as_counterevidence": False,
            },
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
                "actor_spread_count": divergence.get("observed_branch_opportunity_actor_spread_count", "UNKNOWN"),
                "context_spread_state": context_state,
                "concentration_warnings": concentration_warnings,
                "binomial_interval_allowed": False,
                "shrinkage_allowed": False,
            },
            "withdrawal_conditions": [
                "WITHDRAW_IF_SHARED_ANCHOR_ADMISSION_INVALIDATED",
                "WITHDRAW_IF_OUTCOME_SEMANTIC_BINDING_INVALIDATED",
                "WITHDRAW_IF_COMPARISON_ELIGIBILITY_INVALIDATED",
                "WITHDRAW_IF_COMPARABLE_COUNTEREXAMPLE_BINDING_DISAPPEARS",
            ],
            "analyst_action": "REVIEW_BRANCH_EXAMPLES_AND_USE_ONLY_AS_MATCH_LOCAL_VARIATION_CUE",
            "analyst_summary_tr": (
                f"Aynı görünür başlangıçtan çıkan {denominator} sonuç-semantiği çözülmüş dalın "
                f"{numerator}'si SUCCESS, {len(failure_refs)}'i FAILURE olarak gözlendi; "
                "dallar bağımsız tekrar olmadığı için bu oran gerçek başarı olasılığı veya taktik kalite değildir."
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

    variant_to_sequence = _variant_sequence_map(sequence_payload)
    sequence_outcomes = _sequence_outcome_map(sequence_payload)
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
            comparable_counterevidence_candidate = False
        elif not left_sequence or not right_sequence:
            contrast_state = "COMPARABLE_VARIANT_SEQUENCE_BINDING_MISSING_REVIEW_REQUIRED"
            comparable_counterevidence_candidate = False
            reviews.append(f"comparable_variant_sequence_binding_missing:{pair_id}")
        elif left_outcome is None or right_outcome is None:
            contrast_state = "COMPARABLE_VISIBLE_OUTCOME_SEMANTIC_UNRESOLVED_REVIEW_REQUIRED"
            comparable_counterevidence_candidate = False
            reviews.append(f"comparable_visible_outcome_semantic_unresolved:{pair_id}")
        elif left_outcome == right_outcome:
            contrast_state = "COMPARABLE_SAME_VISIBLE_OUTCOME"
            comparable_counterevidence_candidate = False
        else:
            contrast_state = "COMPARABLE_DIFFERENT_VISIBLE_OUTCOME_COUNTEREXAMPLE_CANDIDATE"
            comparable_counterevidence_candidate = True

        record_id = "coc_" + _digest(pair_id, left_variant, right_variant, left_outcome, right_outcome)[:24]
        records.append({
            "comparable_outcome_counterevidence_id": record_id,
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
            "comparable_counterevidence_candidate": comparable_counterevidence_candidate,
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

    handoffs = _safe_finding_handoff_candidates(sequence_payload, records) if not blocks else []

    if blocks:
        status = "FAIL_CLOSED"
    elif reviews or sequence_payload.get("dependency_aware_partial_order_similarity_status") == "REVIEW_REQUIRED" or sequence_payload.get("first_supported_branch_divergence_status") == "REVIEW_REQUIRED":
        status = "REVIEW_REQUIRED"
    else:
        status = "PASS"

    counts = Counter(_clean(row.get("comparable_outcome_contrast_state")) for row in records)
    return {
        "status": status,
        "comparable_outcome_counterevidence_records": records if not blocks else [],
        "comparable_outcome_counterevidence_record_count": len(records) if not blocks else 0,
        "comparable_outcome_contrast_state_counts": dict(sorted(counts.items())) if not blocks else {},
        "comparison_eligible_record_count": sum(1 for row in records if row.get("comparison_eligible")) if not blocks else 0,
        "comparable_counterevidence_candidate_count": sum(1 for row in records if row.get("comparable_counterevidence_candidate")) if not blocks else 0,
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
        "same_timestamp_internal_ordering_allowed": False,
        "source_row_order_is_temporal_truth": False,
        "hard_block_hits": sorted(set(blocks)),
        "review_hits": sorted(set(reviews)),
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
    }
