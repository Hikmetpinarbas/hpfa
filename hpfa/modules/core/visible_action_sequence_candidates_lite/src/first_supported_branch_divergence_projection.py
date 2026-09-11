from __future__ import annotations

import hashlib
import json
from collections import Counter
from typing import Any

CLAIM_CEILING = "OBSERVED_EARLIEST_SUPPORTED_BRANCH_SEMANTIC_DIVERGENCE_CANDIDATE_ONLY"


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
    }


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
        map_id = _clean(branch_map.get("anchor_centered_sequence_branch_map_id"))
        successor_branches = [
            row for row in (branch_map.get("branch_records") or [])
            if isinstance(row, dict) and row.get("branch_direction") == "SUCCESSOR"
        ]
        if len(successor_branches) < 2:
            continue

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

            state_counts = Counter(profile.get("outcome_state") for profile in profiles if profile.get("outcome_state"))
            if len(state_counts) == 1:
                branch_outcome_state = next(iter(state_counts))
            elif len(state_counts) > 1:
                branch_outcome_state = "MIXED_ADMITTED_OUTCOME_SEMANTICS"
            else:
                branch_outcome_state = "OUTCOME_SEMANTIC_NOT_ADMITTED_FOR_DIVERGENCE"

            if missing_ids:
                reviews.append(f"divergence_branch_occurrence_reference_missing:{map_id}")

            branch_profiles.append({
                "neighbor_time_layer_ref": branch.get("neighbor_time_layer_ref"),
                "neighbor_time_candidate": branch.get("neighbor_time_candidate"),
                "neighbor_supporting_action_occurrence_candidate_ids": occurrence_ids,
                "semantic_profiles": profiles,
                "branch_outcome_state": branch_outcome_state,
                "semantic_profile_count": len(profiles),
                "supporting_visible_sequence_candidate_ids": list(
                    branch.get("supporting_visible_sequence_candidate_ids") or []
                ),
                "branch_is_independent_recurrence_support": False,
            })

        success = [row for row in branch_profiles if row["branch_outcome_state"] == "SUCCESS_SEMANTIC_VISIBLE"]
        failure = [row for row in branch_profiles if row["branch_outcome_state"] == "FAILURE_SEMANTIC_VISIBLE"]
        if not success or not failure:
            continue

        divergence_id = "fsbd_" + _digest(
            map_id,
            branch_map.get("anchor_time_layer_ref"),
            sorted((row.get("neighbor_time_layer_ref"), row.get("branch_outcome_state")) for row in branch_profiles),
        )[:24]
        records.append({
            "first_supported_branch_divergence_id": divergence_id,
            "anchor_centered_sequence_branch_map_ref": map_id,
            "team_identity_candidate_id": branch_map.get("team_identity_candidate_id"),
            "period_candidate": branch_map.get("period_candidate"),
            "shared_anchor_time_layer_ref": branch_map.get("anchor_time_layer_ref"),
            "shared_anchor_time_candidate": branch_map.get("anchor_time_candidate"),
            "shared_anchor_action_family_counts": dict(branch_map.get("anchor_action_family_counts") or {}),
            "divergence_level": "FIRST_SUCCESSOR_AFTER_SHARED_VISIBLE_ANCHOR",
            "success_branch_count": len(success),
            "failure_branch_count": len(failure),
            "other_or_unresolved_branch_count": len(branch_profiles) - len(success) - len(failure),
            "branch_profiles": branch_profiles,
            "divergence_is_failure_cause_truth": False,
            "divergence_is_tactical_truth": False,
            "divergence_is_possession_truth": False,
            "branches_are_independent_recurrence_support": False,
            "branch_count_is_recurrence_count": False,
            "outcome_semantics_used_only_after_shared_anchor_admission": True,
            "same_timestamp_internal_ordering_allowed": False,
            "source_row_order_is_temporal_truth": False,
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
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
        "success_failure_semantic_divergence_required": True,
        "raw_label_string_matching_is_outcome_truth": False,
        "branch_count_is_recurrence_count": False,
        "divergence_is_failure_cause_truth": False,
        "divergence_is_tactical_truth": False,
        "branches_are_independent_recurrence_support": False,
        "same_timestamp_internal_ordering_allowed": False,
        "source_row_order_is_temporal_truth": False,
        "hard_block_hits": sorted(set(blocks)),
        "review_hits": sorted(set(reviews)),
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
    }
