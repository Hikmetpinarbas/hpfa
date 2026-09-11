from __future__ import annotations

import hashlib
import json
from typing import Any

CLAIM_CEILING = "MATCH_LOCAL_DEPENDENCY_QUALIFIED_BRANCH_OUTCOME_YIELD_CANDIDATE_ONLY"


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _digest(*values: Any) -> str:
    raw = json.dumps(values, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _occurrence_map(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        _clean(row.get("action_occurrence_candidate_id")): row
        for row in (payload.get("action_occurrence_candidates") or [])
        if isinstance(row, dict) and _clean(row.get("action_occurrence_candidate_id"))
    }


def build_observed_branch_opportunity_yield(
    sequence_payload: dict[str, Any],
    occurrence_payload: dict[str, Any],
) -> dict[str, Any]:
    blocks: list[str] = []
    reviews: list[str] = []

    if sequence_payload.get("first_supported_branch_divergence_status") == "FAIL_CLOSED":
        blocks.append("first_supported_branch_divergence_fail_closed")
    if sequence_payload.get("branch_count_is_recurrence_count") is not False:
        blocks.append("branch_count_recurrence_policy_breached")
    if sequence_payload.get("divergence_branches_are_independent_recurrence_support") is not False:
        blocks.append("branch_independence_policy_breached")
    if sequence_payload.get("canonical_event_count") != "UNKNOWN":
        blocks.append("canonical_event_count_claimed")
    if sequence_payload.get("true_action_count") != "UNKNOWN":
        blocks.append("true_action_count_claimed")
    if sequence_payload.get("production_release") is True:
        blocks.append("production_release_claimed")
    if occurrence_payload.get("canonical_event_count") != "UNKNOWN":
        blocks.append("occurrence_canonical_event_count_claimed")
    if occurrence_payload.get("true_action_count") != "UNKNOWN":
        blocks.append("occurrence_true_action_count_claimed")
    if occurrence_payload.get("production_release") is True:
        blocks.append("occurrence_production_release_claimed")

    occurrence_by_id = _occurrence_map(occurrence_payload)
    divergences = [
        row
        for row in (sequence_payload.get("first_supported_branch_divergence_candidates") or [])
        if isinstance(row, dict)
    ]
    records: list[dict[str, Any]] = []

    for divergence in divergences:
        divergence_id = _clean(divergence.get("first_supported_branch_divergence_id"))
        branch_profiles = [row for row in (divergence.get("branch_profiles") or []) if isinstance(row, dict)]
        success = [row for row in branch_profiles if row.get("branch_outcome_state") == "SUCCESS_SEMANTIC_VISIBLE"]
        failure = [row for row in branch_profiles if row.get("branch_outcome_state") == "FAILURE_SEMANTIC_VISIBLE"]
        resolved = success + failure
        unresolved_count = len(branch_profiles) - len(resolved)
        eligible_denominator = len(resolved)
        success_count = len(success)
        failure_count = len(failure)
        raw_rate = round(success_count / eligible_denominator, 6) if eligible_denominator else None

        actor_ids: set[str] = set()
        team_ids: set[str] = set()
        missing_occurrence_refs: list[str] = []
        supporting_occurrence_ids: list[str] = []
        for branch in resolved:
            for occurrence_id_raw in branch.get("neighbor_supporting_action_occurrence_candidate_ids") or []:
                occurrence_id = _clean(occurrence_id_raw)
                if not occurrence_id:
                    continue
                supporting_occurrence_ids.append(occurrence_id)
                occurrence = occurrence_by_id.get(occurrence_id)
                if occurrence is None:
                    missing_occurrence_refs.append(occurrence_id)
                    continue
                actor_id = _clean(occurrence.get("actor_identity_candidate_id"))
                team_id = _clean(occurrence.get("team_identity_candidate_id"))
                if actor_id:
                    actor_ids.add(actor_id)
                if team_id:
                    team_ids.add(team_id)

        independence_proven = bool(divergence.get("branches_are_independent_recurrence_support") is True)
        admitted_independent_support_count = eligible_denominator if independence_proven else 0
        concentration_warnings = ["SINGLE_SHARED_ANCHOR_CONCENTRATION"]
        if not independence_proven:
            concentration_warnings.append("DEPENDENCY_DOMINATED_SHARED_ANCHOR_BRANCHES")
        if len(actor_ids) == 1 and eligible_denominator:
            concentration_warnings.append("SINGLE_ACTOR_CONCENTRATION")
        if unresolved_count:
            concentration_warnings.append("UNRESOLVED_OUTCOME_BURDEN")
        if missing_occurrence_refs:
            concentration_warnings.append("OCCURRENCE_REFERENCE_COVERAGE_INCOMPLETE")
            reviews.append(f"branch_opportunity_occurrence_reference_missing:{divergence_id}")

        if eligible_denominator == 0:
            support_state = "NO_ELIGIBLE_DENOMINATOR"
        elif not independence_proven:
            support_state = "DESCRIPTIVE_ONLY_DEPENDENCY_DOMINATED"
        else:
            support_state = "MATCH_LOCAL_SUPPORT_REQUIRES_VALIDATED_THRESHOLDS"

        record_id = "boy_" + _digest(divergence_id, supporting_occurrence_ids)[:24]
        records.append({
            "observed_branch_opportunity_yield_id": record_id,
            "first_supported_branch_divergence_ref": divergence_id or None,
            "anchor_centered_sequence_branch_map_ref": divergence.get("anchor_centered_sequence_branch_map_ref"),
            "team_identity_candidate_id": divergence.get("team_identity_candidate_id"),
            "period_candidate": divergence.get("period_candidate"),
            "shared_anchor_time_layer_ref": divergence.get("shared_anchor_time_layer_ref"),
            "opportunity_unit": "ADMITTED_SUCCESS_FAILURE_SUCCESSOR_BRANCH_SEMANTIC",
            "success_numerator": success_count,
            "failure_count": failure_count,
            "eligible_denominator": eligible_denominator,
            "total_visible_branch_count": len(branch_profiles),
            "unresolved_or_other_branch_count": unresolved_count,
            "raw_descriptive_success_rate": raw_rate,
            "resolved_outcome_coverage_numerator": eligible_denominator,
            "resolved_outcome_coverage_denominator": len(branch_profiles),
            "supporting_action_occurrence_candidate_ids": sorted(set(supporting_occurrence_ids)),
            "actor_spread_count": len(actor_ids),
            "team_spread_count": len(team_ids),
            "anchor_spread_count": 1,
            "episode_spread_count": "UNKNOWN",
            "context_spread_state": "PARTIAL_PERIOD_AND_SHARED_ANCHOR_ONLY",
            "dependency_independence_proven": independence_proven,
            "statistical_independence_proven": False,
            "admitted_independent_support_count": admitted_independent_support_count,
            "support_state": support_state,
            "concentration_warnings": sorted(set(concentration_warnings)),
            "missing_occurrence_reference_ids": sorted(set(missing_occurrence_refs)),
            "binomial_interval_allowed": False,
            "shrinkage_allowed": False,
            "prior_used": False,
            "raw_rate_is_true_success_probability": False,
            "raw_rate_is_intrinsic_process_efficiency": False,
            "raw_rate_is_tactical_quality": False,
            "raw_rate_is_causal_superiority": False,
            "success_failure_semantic_is_terminal_outcome_truth": False,
            "branch_count_is_recurrence_count": False,
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "claim_ceiling": CLAIM_CEILING,
        })

    if blocks:
        status = "FAIL_CLOSED"
    elif reviews or sequence_payload.get("first_supported_branch_divergence_status") == "REVIEW_REQUIRED":
        status = "REVIEW_REQUIRED"
    else:
        status = "PASS"

    return {
        "status": status,
        "observed_branch_opportunity_yield_records": records if not blocks else [],
        "observed_branch_opportunity_yield_record_count": len(records) if not blocks else 0,
        "source_first_supported_branch_divergence_candidate_count": len(divergences),
        "raw_rate_requires_explicit_numerator_denominator": True,
        "dependency_qualified_support_required": True,
        "binomial_interval_allowed": False,
        "shrinkage_allowed": False,
        "raw_rate_is_true_success_probability": False,
        "raw_rate_is_intrinsic_process_efficiency": False,
        "raw_rate_is_tactical_quality": False,
        "hard_block_hits": sorted(set(blocks)),
        "review_hits": sorted(set(reviews)),
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
    }
