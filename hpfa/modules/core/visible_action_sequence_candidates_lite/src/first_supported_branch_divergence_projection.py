from __future__ import annotations

import hashlib
import json
from collections import Counter
from typing import Any

CLAIM_CEILING = "OUTCOME_BLIND_FIRST_SUPPORTED_VISIBLE_BRANCH_DIVERGENCE_CANDIDATE_ONLY"
YIELD_CLAIM_CEILING = "MATCH_LOCAL_DEPENDENCY_QUALIFIED_BRANCH_OUTCOME_YIELD_CANDIDATE_ONLY"


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


def _dimension_values(candidate: dict[str, Any], key: str) -> list[str]:
    values: list[Any] = []
    semantic_dimensions = candidate.get("semantic_dimensions") or {}
    raw = semantic_dimensions.get(key)
    if isinstance(raw, list):
        values.extend(raw)
    elif raw not in (None, ""):
        values.append(raw)

    attributes = candidate.get("attributes") or {}
    raw_attr = attributes.get(key)
    if isinstance(raw_attr, list):
        values.extend(raw_attr)
    elif raw_attr not in (None, ""):
        values.append(raw_attr)

    return sorted({_clean(value).upper() for value in values if _clean(value)})


def _semantic_profile(candidate: dict[str, Any]) -> dict[str, Any] | None:
    if candidate.get("provider_semantics_binding_status") != "PASS":
        return None
    if candidate.get("action_occurrence_candidate_is_event_truth") is True:
        return None
    if candidate.get("validated_event_identity") is True:
        return None

    outcome_values = _dimension_values(candidate, "outcome_candidate")
    if not outcome_values:
        return None
    if len(outcome_values) != 1:
        return {
            "outcome_state": "AMBIGUOUS",
            "outcome_values": outcome_values,
            "primary_family_candidate": _clean(candidate.get("primary_family_candidate")).upper() or None,
            "direction_values": _dimension_values(candidate, "direction_candidates"),
            "progression_values": _dimension_values(candidate, "progression_candidates"),
            "zone_values": _dimension_values(candidate, "zone_context_candidates"),
            "actor_identity_candidate_id": _clean(candidate.get("actor_identity_candidate_id")) or None,
            "team_identity_candidate_id": _clean(candidate.get("team_identity_candidate_id")) or None,
        }

    outcome = outcome_values[0]
    if outcome == "SUCCESS":
        state = "SUCCESS_SEMANTIC_VISIBLE"
    elif outcome == "FAILURE":
        state = "FAILURE_SEMANTIC_VISIBLE"
    else:
        state = "OTHER_ADMITTED_OUTCOME_SEMANTIC"

    return {
        "outcome_state": state,
        "outcome_values": outcome_values,
        "primary_family_candidate": _clean(candidate.get("primary_family_candidate")).upper() or None,
        "direction_values": _dimension_values(candidate, "direction_candidates"),
        "progression_values": _dimension_values(candidate, "progression_candidates"),
        "zone_values": _dimension_values(candidate, "zone_context_candidates"),
        "actor_identity_candidate_id": _clean(candidate.get("actor_identity_candidate_id")) or None,
        "team_identity_candidate_id": _clean(candidate.get("team_identity_candidate_id")) or None,
    }


def _branch_outcome_state(profiles: list[dict[str, Any]]) -> str:
    state_counts = Counter(profile.get("outcome_state") for profile in profiles if profile.get("outcome_state"))
    if len(state_counts) == 1:
        return next(iter(state_counts))
    if len(state_counts) > 1:
        return "MIXED_ADMITTED_OUTCOME_SEMANTICS"
    return "OUTCOME_SEMANTIC_NOT_ADMITTED_FOR_CONSEQUENCE_ATTACHMENT"


def build_first_supported_branch_divergence(
    sequence_payload: dict[str, Any],
    occurrence_payload: dict[str, Any],
) -> dict[str, Any]:
    blocks: list[str] = []
    reviews: list[str] = []

    if sequence_payload.get("anchor_centered_sequence_branch_map_status") == "FAIL_CLOSED":
        blocks.append("branch_map_projection_fail_closed")
    if sequence_payload.get("branch_count_is_recurrence_count") is not False:
        blocks.append("branch_count_recurrence_policy_breached")
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
    if occurrence_payload.get("canonical_event_count") != "UNKNOWN":
        blocks.append("occurrence_canonical_event_count_claimed")
    if occurrence_payload.get("true_action_count") != "UNKNOWN":
        blocks.append("occurrence_true_action_count_claimed")
    if occurrence_payload.get("production_release") is True:
        blocks.append("occurrence_production_release_claimed")

    occurrence_by_id = _occurrence_map(occurrence_payload)
    branch_maps = [
        row for row in (sequence_payload.get("anchor_centered_sequence_branch_maps") or [])
        if isinstance(row, dict)
    ]
    records: list[dict[str, Any]] = []

    for branch_map in branch_maps:
        map_id = _clean(
            branch_map.get("branch_map_id")
            or branch_map.get("anchor_centered_sequence_branch_map_id")
        )
        comparable_set_id = _clean(branch_map.get("comparable_set_id"))
        if not map_id:
            blocks.append("branch_map_id_missing")
            continue
        if not comparable_set_id:
            blocks.append(f"divergence_comparable_set_ref_missing:{map_id}")
            continue
        if branch_map.get("eligible_denominator_frozen_before_branch_consequence_attachment") is not True:
            blocks.append(f"divergence_denominator_not_frozen_before_consequence:{map_id}")
            continue
        if branch_map.get("outcome_used_in_comparison_admission") is not False:
            blocks.append(f"divergence_upstream_outcome_leakage:{map_id}")
            continue
        if branch_map.get("outcome_used_in_branch_partition") is not False:
            blocks.append(f"divergence_branch_partition_outcome_leakage:{map_id}")
            continue

        successor_branches = [
            row for row in (branch_map.get("branch_records") or [])
            if isinstance(row, dict) and row.get("branch_direction") == "SUCCESSOR"
        ]
        if len(successor_branches) < 2:
            continue

        # Divergence location is established here from the frozen structural branch
        # partition only. Outcome semantics are deliberately not read until after the
        # divergence identity is fixed.
        structural_branch_identity = sorted(
            (
                _clean(branch.get("branch_id")),
                _clean(branch.get("neighbor_time_layer_ref")),
                tuple(sorted(
                    _clean(value)
                    for value in (branch.get("supporting_visible_sequence_candidate_ids") or [])
                    if _clean(value)
                )),
            )
            for branch in successor_branches
        )
        divergence_id = "fsbd_" + _digest(
            map_id,
            comparable_set_id,
            branch_map.get("anchor_time_layer_ref"),
            structural_branch_identity,
        )[:24]

        branch_profiles: list[dict[str, Any]] = []
        for branch in successor_branches:
            occurrence_ids = [
                _clean(value)
                for value in (branch.get("neighbor_supporting_action_occurrence_candidate_ids") or [])
                if _clean(value)
            ]
            profiles: list[dict[str, Any]] = []
            missing_ids: list[str] = []
            for occurrence_id in occurrence_ids:
                occurrence = occurrence_by_id.get(occurrence_id)
                if occurrence is None:
                    missing_ids.append(occurrence_id)
                    continue
                profile = _semantic_profile(occurrence)
                if profile is not None:
                    profiles.append(profile)

            if missing_ids:
                reviews.append(f"divergence_branch_occurrence_reference_missing:{map_id}")

            branch_profiles.append({
                "branch_id": branch.get("branch_id"),
                "neighbor_time_layer_ref": branch.get("neighbor_time_layer_ref"),
                "neighbor_time_candidate": branch.get("neighbor_time_candidate"),
                "neighbor_action_family_counts": dict(branch.get("neighbor_action_family_counts") or {}),
                "neighbor_supporting_action_occurrence_candidate_ids": occurrence_ids,
                "semantic_profiles": profiles,
                "branch_outcome_state": _branch_outcome_state(profiles),
                "semantic_profile_count": len(profiles),
                "supporting_visible_sequence_candidate_ids": list(
                    branch.get("supporting_visible_sequence_candidate_ids") or []
                ),
                "branch_supporting_sequence_count": int(branch.get("branch_supporting_sequence_count") or 0),
                "outcome_attached_after_divergence_location": True,
                "branch_is_independent_recurrence_support": False,
            })

        success = [row for row in branch_profiles if row["branch_outcome_state"] == "SUCCESS_SEMANTIC_VISIBLE"]
        failure = [row for row in branch_profiles if row["branch_outcome_state"] == "FAILURE_SEMANTIC_VISIBLE"]
        other_or_unresolved = [row for row in branch_profiles if row not in success and row not in failure]

        success_case_n = sum(row.get("branch_supporting_sequence_count", 0) for row in success)
        failure_case_n = sum(row.get("branch_supporting_sequence_count", 0) for row in failure)
        unresolved_case_n = sum(row.get("branch_supporting_sequence_count", 0) for row in other_or_unresolved)
        try:
            eligible_denominator = int(branch_map.get("eligible_denominator_n"))
        except (TypeError, ValueError):
            eligible_denominator = 0
        if eligible_denominator <= 0:
            blocks.append(f"divergence_eligible_denominator_missing:{map_id}")
            continue
        materialized_case_n = success_case_n + failure_case_n + unresolved_case_n
        if materialized_case_n != eligible_denominator:
            reviews.append(f"divergence_branch_support_denominator_mismatch:{map_id}")

        raw_success_rate = round(success_case_n / eligible_denominator, 6)
        actor_ids = {
            _clean(profile.get("actor_identity_candidate_id"))
            for branch in branch_profiles
            for profile in (branch.get("semantic_profiles") or [])
            if _clean(profile.get("actor_identity_candidate_id"))
        }
        if success and failure:
            outcome_contrast_state = "SUCCESS_FAILURE_VISIBLE_AFTER_DIVERGENCE"
        elif success and not failure and not other_or_unresolved:
            outcome_contrast_state = "ALL_ADMITTED_BRANCH_OUTCOMES_SUCCESS_VISIBLE"
        elif failure and not success and not other_or_unresolved:
            outcome_contrast_state = "ALL_ADMITTED_BRANCH_OUTCOMES_FAILURE_VISIBLE"
        elif other_or_unresolved:
            outcome_contrast_state = "OUTCOME_CONTRAST_PARTIAL_OR_UNRESOLVED"
        else:
            outcome_contrast_state = "OUTCOME_CONTRAST_NOT_ADMITTED"

        concentration_warnings = [
            "SINGLE_SHARED_ANCHOR_CONCENTRATION",
            "DEPENDENCY_DOMINATED_SHARED_ANCHOR_BRANCHES",
        ]
        if len(actor_ids) == 1:
            concentration_warnings.append("SINGLE_ACTOR_CONCENTRATION")
        if unresolved_case_n:
            concentration_warnings.append("UNRESOLVED_OUTCOME_BURDEN")
        if materialized_case_n != eligible_denominator:
            concentration_warnings.append("BRANCH_SUPPORT_DENOMINATOR_MISMATCH_REVIEW_REQUIRED")

        records.append({
            "first_supported_branch_divergence_id": divergence_id,
            "anchor_centered_sequence_branch_map_ref": map_id,
            "comparable_set_id": comparable_set_id,
            "comparison_question_id": branch_map.get("comparison_question_id"),
            "team_identity_candidate_id": branch_map.get("team_identity_candidate_id"),
            "period_candidate": branch_map.get("period_candidate"),
            "shared_anchor_time_layer_ref": branch_map.get("anchor_time_layer_ref"),
            "shared_anchor_time_candidate": branch_map.get("anchor_time_candidate"),
            "shared_anchor_action_family_counts": dict(branch_map.get("anchor_action_family_counts") or {}),
            "shared_prefix_candidate": branch_map.get("shared_prefix_candidate"),
            "shared_prefix_support_n": branch_map.get("shared_prefix_support_n"),
            "divergence_level": "FIRST_SUCCESSOR_AFTER_SHARED_VISIBLE_ANCHOR",
            "first_supported_divergence_state": "RESOLVED_AT_IMMEDIATE_POST_ANCHOR_LAYER",
            "structural_successor_branch_count": len(successor_branches),
            "divergence_located_without_outcome": True,
            "outcome_used_in_divergence_location": False,
            "eligible_denominator_frozen_before_divergence_outcome_attachment": True,
            "success_branch_count": len(success),
            "failure_branch_count": len(failure),
            "other_or_unresolved_branch_count": len(other_or_unresolved),
            "outcome_contrast_state": outcome_contrast_state,
            "branch_profiles": branch_profiles,
            "observed_branch_opportunity_unit": "FROZEN_COMPARABLE_EDGE_VARIANT",
            "observed_branch_opportunity_success_numerator": success_case_n,
            "observed_branch_opportunity_failure_numerator": failure_case_n,
            "observed_branch_opportunity_unresolved_numerator": unresolved_case_n,
            "observed_branch_opportunity_eligible_denominator": eligible_denominator,
            "observed_branch_opportunity_raw_success_rate": raw_success_rate,
            "observed_branch_opportunity_total_visible_branch_count": len(branch_profiles),
            "observed_branch_opportunity_actor_spread_count": len(actor_ids),
            "observed_branch_opportunity_anchor_spread_count": 1,
            "observed_branch_opportunity_episode_spread_count": "UNKNOWN",
            "observed_branch_opportunity_context_spread_state": "PARTIAL_PERIOD_AND_SHARED_ANCHOR_ONLY",
            "observed_branch_opportunity_admitted_independent_support_count": 0,
            "observed_branch_opportunity_dependency_independence_proven": False,
            "observed_branch_opportunity_statistical_independence_proven": False,
            "observed_branch_opportunity_support_state": "DESCRIPTIVE_ONLY_DEPENDENCY_DOMINATED",
            "observed_branch_opportunity_concentration_warnings": sorted(set(concentration_warnings)),
            "observed_branch_opportunity_binomial_interval_allowed": False,
            "observed_branch_opportunity_shrinkage_allowed": False,
            "observed_branch_opportunity_prior_used": False,
            "observed_branch_opportunity_raw_rate_is_true_success_probability": False,
            "observed_branch_opportunity_raw_rate_is_intrinsic_process_efficiency": False,
            "observed_branch_opportunity_raw_rate_is_tactical_quality": False,
            "observed_branch_opportunity_claim_ceiling": YIELD_CLAIM_CEILING,
            "divergence_is_failure_cause_truth": False,
            "divergence_is_tactical_truth": False,
            "divergence_is_possession_truth": False,
            "branches_are_independent_recurrence_support": False,
            "branch_count_is_recurrence_count": False,
            "outcome_semantics_used_only_after_divergence_location": True,
            "same_timestamp_internal_ordering_allowed": False,
            "source_row_order_is_temporal_truth": False,
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
            "claim_ceiling": CLAIM_CEILING,
        })

    if blocks:
        status = "FAIL_CLOSED"
    elif reviews or sequence_payload.get("anchor_centered_sequence_branch_map_status") == "REVIEW_REQUIRED":
        status = "REVIEW_REQUIRED"
    else:
        status = "PASS"

    return {
        "status": status,
        "first_supported_branch_divergence_candidates": records if not blocks else [],
        "first_supported_branch_divergence_candidate_count": len(records) if not blocks else 0,
        "source_anchor_centered_sequence_branch_map_count": len(branch_maps),
        "success_failure_semantic_divergence_required": False,
        "divergence_requires_frozen_comparable_set": True,
        "divergence_located_without_outcome": True,
        "outcome_used_in_divergence_location": False,
        "outcome_semantics_attached_only_after_divergence_location": True,
        "raw_label_string_matching_is_outcome_truth": False,
        "branch_count_is_recurrence_count": False,
        "divergence_is_failure_cause_truth": False,
        "divergence_is_tactical_truth": False,
        "branches_are_independent_recurrence_support": False,
        "opportunity_yield_requires_explicit_numerator_denominator": True,
        "opportunity_yield_denominator_frozen_before_outcome": True,
        "opportunity_yield_dependency_qualified_support_required": True,
        "opportunity_yield_binomial_interval_allowed": False,
        "opportunity_yield_shrinkage_allowed": False,
        "opportunity_yield_is_intrinsic_process_efficiency": False,
        "same_timestamp_internal_ordering_allowed": False,
        "source_row_order_is_temporal_truth": False,
        "hard_block_hits": sorted(set(blocks)),
        "review_hits": sorted(set(reviews)),
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
    }
